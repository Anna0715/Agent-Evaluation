#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from quality_sync import SyncOptions, sync_via_api, sync_via_dispatch


class _FakeSyncHandler(BaseHTTPRequestHandler):
    received: dict | None = None

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        type(self).received = {"headers": dict(self.headers), "body": body}
        payload = json.dumps({"ok": True, "report_url": "https://example.com/r/1"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:
        return


class SyncApiClientTests(unittest.TestCase):
    def test_sync_via_api_posts_multipart(self) -> None:
        xlsx = Path(__file__).with_name("周报追问Agent全面评测用例.xlsx")
        if not xlsx.exists():
            self.skipTest("xlsx fixture missing")

        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeSyncHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            opts = SyncOptions(
                xlsx=xlsx,
                sync_url=f"http://127.0.0.1:{port}",
                batch_id="test-batch",
            )
            result = sync_via_api(opts)
            self.assertTrue(result["ok"])
            self.assertIn(b"PK", _FakeSyncHandler.received["body"])
            auth = _FakeSyncHandler.received["headers"].get("Authorization", "")
            self.assertEqual(auth, "")
        finally:
            server.shutdown()


class SyncDispatchTests(unittest.TestCase):
    def test_dispatch_requires_token(self) -> None:
        opts = SyncOptions(xlsx=Path(__file__))
        with self.assertRaises(ValueError):
            sync_via_dispatch(opts)

    @mock.patch("quality_sync._github_api")
    @mock.patch("quality_sync._guess_github_repository", return_value="org/repo")
    def test_dispatch_uploads_and_triggers_workflow(self, _repo: mock.MagicMock, api: mock.MagicMock) -> None:
        xlsx = Path(__file__)
        api.side_effect = [
            {"sha": "abc"},
            {},
            {},
        ]
        opts = SyncOptions(
            xlsx=xlsx,
            github_token="token",
            github_repository="org/repo",
            batch_id="b1",
        )
        result = sync_via_dispatch(opts)
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "dispatch")
        self.assertEqual(api.call_count, 3)
        put_call = api.call_args_list[1]
        self.assertEqual(put_call.args[0], "PUT")


if __name__ == "__main__":
    unittest.main()
