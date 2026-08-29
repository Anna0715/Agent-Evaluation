#!/usr/bin/env python3
"""本地质检复核台。"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
FIXTURES_DIR = REPO_ROOT / "fixtures" / "online"
ARTIFACTS_REVIEWS_DIR = REPO_ROOT / "artifacts" / "reviews"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from env_config import test_case_xlsx_path  # noqa: E402
from publish_quality_report import apply_reviews_xlsx, write_local_report  # noqa: E402

DEFAULT_PORT = 8765
OUT_DIR = SCRIPT_DIR / "report_live"
REVIEWS_PATH = ARTIFACTS_REVIEWS_DIR / "zelto-reviews-live.json"
DEFAULT_XLSX = test_case_xlsx_path()


class LiveState:
    def __init__(self, xlsx: Path, sheet: str, date: str, port: int) -> None:
        self.xlsx = xlsx
        self.sheet = sheet
        self.date = date
        self.port = port
        self.lock = threading.Lock()
        self.saved_at = ""

    def generate(self) -> dict:
        return write_local_report(str(self.xlsx), self.sheet, self.date, OUT_DIR, REVIEWS_PATH)

    def save_reviews(self, doc: dict) -> dict:
        with self.lock:
            doc = dict(doc)
            REVIEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
            REVIEWS_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.saved_at = datetime.now().isoformat(timespec="seconds")
            n = apply_reviews_xlsx(str(self.xlsx), self.sheet, doc, replace_all=True)
            self.generate()
            return {"ok": True, "written": n, "savedAt": self.saved_at, "xlsx": str(self.xlsx)}


STATE: LiveState | None = None


class ReviewHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # noqa: ARG002
        return

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            assert STATE is not None
            self._send_json(200, {"ok": True, "date": STATE.date, "xlsx": str(STATE.xlsx), "savedAt": STATE.saved_at})
            return
        target = OUT_DIR / "index.html" if path in {"/", "/index.html"} else OUT_DIR / path.lstrip("/")
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return
        content = target.read_bytes()
        ctype = "text/html; charset=utf-8" if target.suffix == ".html" else "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/review":
            self.send_error(404)
            return
        assert STATE is not None
        try:
            self._send_json(200, STATE.save_reviews(self._read_json()))
        except Exception as exc:  # pragma: no cover
            self._send_json(500, {"ok": False, "error": str(exc)})


def main() -> int:
    global STATE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--xlsx", default=str(DEFAULT_XLSX))
    parser.add_argument("--record-sheet", default="执行记录")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    xlsx = Path(args.xlsx)
    if not xlsx.is_absolute():
        xlsx = FIXTURES_DIR / xlsx
    STATE = LiveState(xlsx, args.record_sheet, args.date, args.port)
    STATE.generate()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), ReviewHandler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"[SERVE] {url}")
    print(f"[XLSX]  {STATE.xlsx}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
