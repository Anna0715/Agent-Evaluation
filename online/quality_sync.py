#!/usr/bin/env python3
"""本地评测完成后，同步发布质检报告。

模式：
  api    — POST 到远程 quality_sync_server（推荐，发布在 CI/CD 侧执行）
  local  — 本机直接 publish_quality_report（开发/无远端时）
  dispatch — 触发 GitHub Actions workflow（纯 CI/CD 发布）

环境变量：
  QUALITY_SYNC_URL    远端同步 API，如 http://sync-host:8787
  QUALITY_SYNC_TOKEN  Bearer token，与服务器 QUALITY_SYNC_TOKEN 一致
  PAGES_REPO          local 模式 Pages 仓库本地路径
  GITHUB_TOKEN        dispatch 模式 PAT（repo + workflow）
  GITHUB_REPOSITORY   dispatch 模式 owner/repo，默认从 git remote 推断

用法：
  python quality_sync.py
  python quality_sync.py --mode api --sync-url http://127.0.0.1:8787
  python run_report_agent_cases.py --case-ids WA-001 --sync
"""

from __future__ import annotations

import argparse
import io
import json
import mimetypes
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
FIXTURES_DIR = REPO_ROOT / "fixtures" / "online"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from env_config import test_case_xlsx_path  # noqa: E402

DEFAULT_XLSX = test_case_xlsx_path()
SYNC_URL_ENV = "QUALITY_SYNC_URL"
SYNC_TOKEN_ENV = "QUALITY_SYNC_TOKEN"
DEFAULT_WORKFLOW = "publish-agent-quality-report.yml"
DEFAULT_STAGING_REL = "online/.sync-staging/xlsx"


@dataclass
class SyncOptions:
    xlsx: Path
    date: str = ""
    batch_id: str = ""
    record_sheet: str = "执行记录"
    reviews: Path | None = None
    no_webhook: bool = False
    force_webhook: bool = False
    delta_case_ids: str = ""
    delta_always: bool = False
    no_push: bool = False
    pages_repo: Path | None = None
    sync_url: str = ""
    sync_token: str = ""
    github_token: str = ""
    github_repository: str = ""
    workflow_file: str = DEFAULT_WORKFLOW
    timeout: float = 600.0

    def resolved_date(self) -> str:
        return self.date or datetime.now().strftime("%Y-%m-%d")

    def resolved_batch_id(self) -> str:
        return self.batch_id or datetime.now().strftime("sync-%Y%m%dT%H%M%S")


def _guess_github_repository(cwd: Path | None = None) -> str:
    env = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
    if env:
        return env
    try:
        out = subprocess.check_output(
            ["git", "-C", str(cwd or REPO_ROOT), "remote", "get-url", "origin"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    if out.endswith(".git"):
        out = out[:-4]
    if "github.com:" in out:
        return out.split("github.com:", 1)[1]
    if "github.com/" in out:
        return out.split("github.com/", 1)[1]
    return ""


def _auth_headers(token: str) -> dict[str, str]:
    headers = {"User-Agent": "quality-sync-client/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def sync_via_api(opts: SyncOptions) -> dict[str, Any]:
    url = (opts.sync_url or os.environ.get(SYNC_URL_ENV) or "").strip().rstrip("/")
    token = (opts.sync_token or os.environ.get(SYNC_TOKEN_ENV) or "").strip()
    if not url:
        raise ValueError(f"api 模式需要 --sync-url 或 ${SYNC_URL_ENV}")

    endpoint = urljoin(url + "/", "api/v1/quality/sync")
    boundary = f"----quality-sync-{uuid.uuid4().hex}"
    body = io.BytesIO()
    fields: list[tuple[str, str]] = [
        ("date", opts.resolved_date()),
        ("batch_id", opts.resolved_batch_id()),
        ("record_sheet", opts.record_sheet),
        ("no_webhook", "1" if opts.no_webhook else "0"),
        ("force_webhook", "1" if opts.force_webhook else "0"),
        ("delta_case_ids", opts.delta_case_ids or ""),
        ("delta_always", "1" if opts.delta_always else "0"),
    ]
    for key, value in fields:
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.write(f"{value}\r\n".encode())

    xlsx_bytes = opts.xlsx.read_bytes()
    mime = mimetypes.guess_type(opts.xlsx.name)[0] or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    body.write(f"--{boundary}\r\n".encode())
    body.write(
        f'Content-Disposition: form-data; name="xlsx"; filename="{opts.xlsx.name}"\r\n'.encode()
    )
    body.write(f"Content-Type: {mime}\r\n\r\n".encode())
    body.write(xlsx_bytes)
    body.write(b"\r\n")

    if opts.reviews and opts.reviews.exists():
        reviews_bytes = opts.reviews.read_bytes()
        body.write(f"--{boundary}\r\n".encode())
        body.write(
            f'Content-Disposition: form-data; name="reviews"; filename="{opts.reviews.name}"\r\n'.encode()
        )
        body.write(b"Content-Type: application/json\r\n\r\n")
        body.write(reviews_bytes)
        body.write(b"\r\n")

    body.write(f"--{boundary}--\r\n".encode())
    raw = body.getvalue()

    req = Request(
        endpoint,
        data=raw,
        method="POST",
        headers={
            **_auth_headers(token),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(raw)),
        },
    )
    try:
        with urlopen(req, timeout=opts.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"sync API HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"sync API 连接失败: {exc}") from exc

    if not payload.get("ok"):
        raise RuntimeError(payload.get("error") or "sync API 返回失败")
    return payload


def sync_via_local(opts: SyncOptions) -> dict[str, Any]:
    pages_repo = opts.pages_repo or Path(os.environ.get("PAGES_REPO") or "")
    if not pages_repo or not Path(pages_repo).exists():
        raise ValueError("local 模式需要 --pages-repo 或 $PAGES_REPO")

    import argparse as ap

    from publish_quality_report import publish_to_pages

    args = ap.Namespace(
        xlsx=str(opts.xlsx),
        record_sheet=opts.record_sheet,
        date=opts.resolved_date(),
        pages_repo=str(pages_repo),
        no_push=opts.no_push,
        reviews=str(opts.reviews) if opts.reviews else "",
        batch_id=opts.resolved_batch_id(),
        webhook_url=os.environ.get("QUALITY_WEBHOOK_URL", ""),
        webhook_at=os.environ.get("QUALITY_WEBHOOK_AT_USERS", ""),
        no_webhook=opts.no_webhook,
        force_webhook=opts.force_webhook,
        delta_case_ids=opts.delta_case_ids,
        delta_always=opts.delta_always,
    )
    result = publish_to_pages(args)
    return {"ok": True, **result}


def _github_api(method: str, url: str, token: str, payload: dict | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        **_auth_headers(token),
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, method=method, headers=headers)
    with urlopen(req, timeout=120) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw.strip() else {}


def sync_via_dispatch(opts: SyncOptions) -> dict[str, Any]:
    token = (opts.github_token or os.environ.get("GITHUB_TOKEN") or "").strip()
    repo = (opts.github_repository or _guess_github_repository() or "").strip()
    if not token:
        raise ValueError("dispatch 模式需要 --github-token 或 $GITHUB_TOKEN")
    if not repo:
        raise ValueError("dispatch 模式需要 --github-repository 或 $GITHUB_REPOSITORY")

    xlsx_bytes = opts.xlsx.read_bytes()
    import base64

    content_b64 = base64.b64encode(xlsx_bytes).decode("ascii")
    staging_path = DEFAULT_STAGING_REL
    file_url = f"https://api.github.com/repos/{repo}/contents/{staging_path}"

    sha = None
    try:
        existing = _github_api("GET", file_url, token)
        sha = existing.get("sha")
    except HTTPError as exc:
        if exc.code != 404:
            raise RuntimeError(f"读取 staging 文件失败 HTTP {exc.code}") from exc

    commit_msg = f"quality-sync staging {opts.resolved_batch_id()}"
    put_payload: dict[str, Any] = {
        "message": commit_msg,
        "content": content_b64,
        "branch": "main",
    }
    if sha:
        put_payload["sha"] = sha
    _github_api("PUT", file_url, token, put_payload)

    dispatch_url = f"https://api.github.com/repos/{repo}/actions/workflows/{opts.workflow_file}/dispatches"
    _github_api(
        "POST",
        dispatch_url,
        token,
        {
            "ref": "main",
            "inputs": {
                "date": opts.resolved_date(),
                "batch_id": opts.resolved_batch_id(),
                "no_webhook": "true" if opts.no_webhook else "false",
                "force_webhook": "true" if opts.force_webhook else "false",
            },
        },
    )
    return {
        "ok": True,
        "mode": "dispatch",
        "repository": repo,
        "workflow": opts.workflow_file,
        "batch_id": opts.resolved_batch_id(),
        "message": "已提交 staging xlsx 并触发 GitHub Actions 发布",
    }


def sync_report(opts: SyncOptions, *, mode: str = "api") -> dict[str, Any]:
    if not opts.xlsx.exists():
        raise FileNotFoundError(f"xlsx 不存在: {opts.xlsx}")
    if mode == "api":
        return sync_via_api(opts)
    if mode == "local":
        return sync_via_local(opts)
    if mode == "dispatch":
        return sync_via_dispatch(opts)
    raise ValueError(f"未知 mode: {mode}")


def sync_after_run(
    xlsx: Path | str,
    *,
    mode: str = "",
    sync_url: str = "",
    sync_token: str = "",
    pages_repo: str = "",
    no_webhook: bool = False,
    force_webhook: bool = False,
    delta_case_ids: str = "",
    batch_id: str = "",
) -> dict[str, Any]:
    """run_report_agent_cases 跑完后调用。"""
    resolved_mode = (mode or os.environ.get("QUALITY_SYNC_MODE") or "api").strip().lower()
    if resolved_mode == "api" and not (sync_url or os.environ.get(SYNC_URL_ENV)):
        resolved_mode = "local" if (pages_repo or os.environ.get("PAGES_REPO")) else "api"
    opts = SyncOptions(
        xlsx=Path(xlsx),
        sync_url=sync_url,
        sync_token=sync_token,
        pages_repo=Path(pages_repo) if pages_repo else None,
        no_webhook=no_webhook,
        force_webhook=force_webhook,
        delta_case_ids=delta_case_ids,
        batch_id=batch_id,
    )
    return sync_report(opts, mode=resolved_mode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xlsx", default=str(DEFAULT_XLSX))
    parser.add_argument("--record-sheet", default="执行记录")
    parser.add_argument("--date", default="")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--reviews", default="", help="可选复核 JSON")
    parser.add_argument(
        "--mode",
        choices=("api", "local", "dispatch"),
        default=os.environ.get("QUALITY_SYNC_MODE", "api"),
    )
    parser.add_argument("--sync-url", default=os.environ.get(SYNC_URL_ENV, ""))
    parser.add_argument("--sync-token", default=os.environ.get(SYNC_TOKEN_ENV, ""))
    parser.add_argument("--pages-repo", default=os.environ.get("PAGES_REPO", ""))
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--no-webhook", action="store_true")
    parser.add_argument("--force-webhook", action="store_true")
    parser.add_argument("--delta-case-ids", default="")
    parser.add_argument("--delta-always", action="store_true")
    parser.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--github-repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    parser.add_argument("--timeout", type=float, default=600.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    opts = SyncOptions(
        xlsx=Path(args.xlsx),
        date=args.date,
        batch_id=args.batch_id,
        record_sheet=args.record_sheet,
        reviews=Path(args.reviews) if args.reviews else None,
        no_webhook=args.no_webhook,
        force_webhook=args.force_webhook,
        delta_case_ids=args.delta_case_ids,
        delta_always=args.delta_always,
        no_push=args.no_push,
        pages_repo=Path(args.pages_repo) if args.pages_repo else None,
        sync_url=args.sync_url,
        sync_token=args.sync_token,
        github_token=args.github_token,
        github_repository=args.github_repository,
        workflow_file=args.workflow,
        timeout=args.timeout,
    )
    try:
        result = sync_report(opts, mode=args.mode)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"[SYNC-ERROR] {exc}", file=sys.stderr)
        return 1
    print(f"[SYNC-OK] {json.dumps(result, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
