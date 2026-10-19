"""Real Chromium tests for streaming SSR, large assets and canonical redirects.

These localhost fixtures reproduce failures from an independent adversarial audit.
"""

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pqlqa.runner import inspect


class StreamLargeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/docs":
            self.send_response(301)
            self.send_header("Location", "/docs/")
            self.end_headers()
            return
        if self.path == "/docs/":
            return self._small("<title>Docs</title><h1>Docs</h1>")
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            try:
                self.wfile.write(b"<title>Streaming</title><h1>Streaming</h1>")
                self.wfile.flush()
                for i in range(11):
                    time.sleep(1)
                    self.wfile.write(f"<p>part {i}</p>".encode())
                    self.wfile.flush()
                self.wfile.write(b"</html>")
            except OSError:
                pass
            self.close_connection = True
            return
        if self.path == "/large-page":
            return self._small(
                "<title>Large</title><h1>Large</h1>"
                "<script>fetch('/large.bin').catch(()=>{})</script>"
            )
        if self.path == "/large.bin":
            count = 120
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(count * 1024 * 1024))
            self.end_headers()
            data = b"\0" * (1024 * 1024)
            try:
                for _ in range(count):
                    self.wfile.write(data)
            except OSError:
                pass
            return
        self.send_response(404)
        self.end_headers()

    def _small(self, html):
        content = html.encode("utf8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *_args):
        return


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium fixture opt-in")
def test_large_asset_and_streaming_page_do_not_corrupt_reports(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), StreamLargeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report = inspect(
            f"http://127.0.0.1:{server.server_port}/",
            tmp_path,
            paths=["/large-page", "/stream", "/docs"],
        )
        seen = [(c.page_path, c.viewport, c.check_id) for c in report.checks]
        assert len(seen) == len(set(seen)), "Duplicate or contradictory check IDs"
        navigation = [c for c in report.checks if c.check_id == "NAVIGATION"]
        assert len(navigation) == 6
        assert all(c.status == "PASS" for c in navigation), [
            (c.page_path, c.viewport, c.observed) for c in navigation
        ]
        assert len(report.screenshots) == 6
        redirects = [
            c for c in report.checks
            if c.page_path == "/docs" and c.check_id == "REDIRECTS_REFUSED"
        ]
        assert len(redirects) == 2
        assert all(c.status == "PASS" for c in redirects)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
