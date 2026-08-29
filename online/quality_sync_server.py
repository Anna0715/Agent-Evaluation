#!/usr/bin/env python3
"""质检报告同步 API（部署在 CI/CD / 内网 Runner 上）。

本地跑完 case 后 POST 执行记录 xlsx，服务端发布 GitHub Pages 并返回报告 URL。

接口：
  GET  /api/v1/quality/health
  POST /api/v1/quality/sync   multipart: xlsx (+ 可选 reviews)

鉴权：Header Authorization: Bearer <QUALITY_SYNC_TOKEN>

用法（Runner 上）：
  export QUALITY_SYNC_TOKEN=...
  export PAGES_REPO=/data/Agent_report
  export PAGES_GIT_URL=git@github.com:Anna0715/Agent_report.git
  python quality_sync_server.py --host 0.0.0.0 --port 8787
"""

from __future__ import annotations

import argparse
import cgi
import io
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from quality_sync import SYNC_TOKEN_ENV  # noqa: E402

DEFAULT_PORT = 8787
DEFAULT_XLSX_NAME = "周报追问Agent全面评测用例.xlsx"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class SyncServerState:
    def __init__(
        self,
        *,
        token: str,
        pages_repo: Path,
        pages_git_url: str,
        staging_dir: Path,
        default_record_sheet: str,
    ) -> None:
        self.token = token.strip()
        self.pages_repo = pages_repo
        self.pages_git_url = pages_git_url.strip()
        self.staging_dir = staging_dir
        self.default_record_sheet = default_record_sheet
        self.lock = threading.Lock()
        self.last_sync_at = ""
        self.last_batch_id = ""
        self.last_report_url = ""

    def ensure_pages_repo(self) -> None:
        if (self.pages_repo / ".git").is_dir():
            subprocess.run(["git", "-C", str(self.pages_repo), "pull", "--ff-only"], check=False)
            return
        self.pages_repo.parent.mkdir(parents=True, exist_ok=True)
        if not self.pages_git_url:
            raise RuntimeError("PAGES_GIT_URL 未配置，无法 clone Pages 仓库")
        subprocess.run(["git", "clone", self.pages_git_url, str(self.pages_repo)], check=True)

    def handle_sync(self, fields: dict[str, str], files: dict[str, tuple[str, bytes]]) -> dict[str, Any]:
        if "xlsx" not in files:
            raise ValueError("缺少 multipart 字段 xlsx")
        filename, xlsx_bytes = files["xlsx"]
        if len(xlsx_bytes) > MAX_UPLOAD_BYTES:
            raise ValueError(f"xlsx 超过上限 {MAX_UPLOAD_BYTES} bytes")
        if not xlsx_bytes.startswith(b"PK"):
            raise ValueError("xlsx 文件格式无效")

        date = (fields.get("date") or datetime.now().strftime("%Y-%m-%d")).strip()
        batch_id = (fields.get("batch_id") or datetime.now().strftime("sync-%Y%m%dT%H%M%S")).strip()
        record_sheet = (fields.get("record_sheet") or self.default_record_sheet).strip()
        no_webhook = fields.get("no_webhook", "0") in ("1", "true", "True")
        force_webhook = fields.get("force_webhook", "0") in ("1", "true", "True")
        delta_case_ids = (fields.get("delta_case_ids") or "").strip()
        delta_always = fields.get("delta_always", "0") in ("1", "true", "True")

        self.staging_dir.mkdir(parents=True, exist_ok=True)
        staged_xlsx = self.staging_dir / DEFAULT_XLSX_NAME
        staged_xlsx.write_bytes(xlsx_bytes)

        reviews_path = ""
        if "reviews" in files:
            _, reviews_bytes = files["reviews"]
            reviews_file = self.staging_dir / f"reviews-{batch_id}.json"
            reviews_file.write_bytes(reviews_bytes)
            reviews_path = str(reviews_file)

        with self.lock:
            self.ensure_pages_repo()
            import argparse as ap

            from publish_quality_report import publish_to_pages

            args = ap.Namespace(
                xlsx=str(staged_xlsx),
                record_sheet=record_sheet,
                date=date,
                pages_repo=str(self.pages_repo),
                no_push=False,
                reviews=reviews_path,
                batch_id=batch_id,
                webhook_url=os.environ.get("QUALITY_WEBHOOK_URL", ""),
                webhook_at=os.environ.get("QUALITY_WEBHOOK_AT_USERS", ""),
                no_webhook=no_webhook,
                force_webhook=force_webhook,
                delta_case_ids=delta_case_ids,
                delta_always=delta_always,
            )
            result = publish_to_pages(args)

        self.last_sync_at = datetime.now().isoformat(timespec="seconds")
        self.last_batch_id = batch_id
        self.last_report_url = result.get("report_url", "")
        return {
            "ok": True,
            "batch_id": batch_id,
            "date": date,
            "uploaded_as": filename or DEFAULT_XLSX_NAME,
            **result,
        }


def _parse_bearer(header: str) -> str:
    raw = (header or "").strip()
    if raw.lower().startswith("bearer "):
        return raw[7:].strip()
    return ""


def _send_json(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(raw)


STATE: SyncServerState | None = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        if self.path.startswith("/api/"):
            super().log_message(fmt, *args)

    def do_GET(self) -> None:
        assert STATE is not None
        path = urlparse(self.path).path
        if path in ("/api/v1/quality/health", "/api/v1/quality/health/"):
            _send_json(
                self,
                {
                    "ok": True,
                    "service": "quality-sync",
                    "last_sync_at": STATE.last_sync_at,
                    "last_batch_id": STATE.last_batch_id,
                    "last_report_url": STATE.last_report_url,
                    "pages_repo": str(STATE.pages_repo),
                },
            )
            return
        self.send_error(404)

    def do_POST(self) -> None:
        assert STATE is not None
        path = urlparse(self.path).path
        if path not in ("/api/v1/quality/sync", "/api/v1/quality/sync/"):
            self.send_error(404)
            return

        if STATE.token:
            token = _parse_bearer(self.headers.get("Authorization", ""))
            if token != STATE.token:
                _send_json(self, {"ok": False, "error": "unauthorized"}, 401)
                return

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_UPLOAD_BYTES + 1024 * 1024:
            _send_json(self, {"ok": False, "error": "invalid content length"}, 400)
            return

        ctype = self.headers.get("Content-Type") or ""
        if "multipart/form-data" not in ctype:
            _send_json(self, {"ok": False, "error": "expected multipart/form-data"}, 400)
            return

        raw = self.rfile.read(length)
        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": ctype,
            "CONTENT_LENGTH": str(len(raw)),
        }
        fields: dict[str, str] = {}
        files: dict[str, tuple[str, bytes]] = {}
        fs = cgi.FieldStorage(fp=io.BytesIO(raw), environ=environ, headers=self.headers)
        if not fs.list:
            _send_json(self, {"ok": False, "error": "empty multipart body"}, 400)
            return
        for item in fs.list:
            if item.filename:
                files[item.name] = (item.filename, item.file.read())
            else:
                fields[item.name] = item.value if isinstance(item.value, str) else str(item.value)

        try:
            result = STATE.handle_sync(fields, files)
            _send_json(self, result)
        except Exception as exc:  # noqa: BLE001
            _send_json(self, {"ok": False, "error": str(exc)}, 500)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("QUALITY_SYNC_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("QUALITY_SYNC_PORT", DEFAULT_PORT)))
    parser.add_argument("--token", default=os.environ.get(SYNC_TOKEN_ENV, ""))
    parser.add_argument("--pages-repo", default=os.environ.get("PAGES_REPO", ""))
    parser.add_argument("--pages-git-url", default=os.environ.get("PAGES_GIT_URL", ""))
    parser.add_argument(
        "--staging-dir",
        default=str(SCRIPT_DIR / ".sync-staging"),
        help="接收上传 xlsx 的暂存目录",
    )
    parser.add_argument("--record-sheet", default="执行记录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pages_repo = Path(args.pages_repo) if args.pages_repo else SCRIPT_DIR / ".pages-repo"
    global STATE
    STATE = SyncServerState(
        token=args.token,
        pages_repo=pages_repo,
        pages_git_url=args.pages_git_url,
        staging_dir=Path(args.staging_dir),
        default_record_sheet=args.record_sheet,
    )
    if not STATE.token:
        print("[WARN] QUALITY_SYNC_TOKEN 未设置，API 无鉴权", flush=True)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[SYNC-SERVER] http://{args.host}:{args.port}/api/v1/quality/sync", flush=True)
    print(f"[SYNC-SERVER] pages_repo={pages_repo}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] quality sync server")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
