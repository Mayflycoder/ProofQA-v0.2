"""Round 3 release gates: malformed resources, redirects and status integrity.

Every fixture is isolated to localhost and exercises a real Chromium browser.
"""

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pqlqa.runner import inspect


class MalformedFixture(BaseHTTPRequestHandler):
    posts = 0

    def do_POST(self):
        type(self).posts += 1
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path == "/typo":
            html = (
                '<!doctype html><meta name="viewport" content="width=device-width">'
                '<title>Valid page, broken image</title><h1>Hello</h1>'
                '<img src="http://cdn..example.test/one.png" alt="Oops">'
            )
        elif self.path == "/redir-badport":
            self.send_response(302)
            self.send_header("Location", "http://cdn.example.test:99999/bad")
            self.end_headers()
            return
        elif self.path == "/redir-badipv6":
            self.send_response(302)
            self.send_header("Location", "http://[malformed-ipv6/path")
            self.end_headers()
            return
        elif self.path == "/auto-post":
            html = (
                '<!doctype html><title>Form</title><h1>Form</h1>'
                '<form id="f" action="/save" method="POST"></form>'
                '<script>setTimeout(()=>document.getElementById("f").submit(),70)</script>'
            )
        elif self.path == "/status404":
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<title>404</title><h1>404</h1>")
            return
        elif self.path == "/analytics":
            html = (
                '<!doctype html><meta name="viewport" content="width=device-width">'
                '<title>Analytics</title><h1>Hello</h1>'
                '<script src="http://127.0.0.1:1/analytics.js" async></script>'
            )
        else:
            self.send_response(404)
            self.end_headers()
            return
        payload = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        return


@pytest.fixture
def isolated_site():
    MalformedFixture.posts = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), MalformedFixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium opt-in")
def test_bad_image_url_is_not_a_viewport_wide_failure(isolated_site, tmp_path):
    report = inspect(isolated_site, tmp_path, paths=["/typo"])
    checks = {(c.viewport, c.check_id): c for c in report.checks}
    for viewport in ("desktop", "mobile"):
        assert checks[viewport, "NAVIGATION"].status == "PASS"
        assert checks[viewport, "OFF_ORIGIN_REQUESTS"].status == "WARN"
        assert checks[viewport, "SCREENSHOT"].status == "PASS"
    assert "function takes exactly" not in str(report.to_dict())


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium opt-in")
def test_invalid_redirect_is_refused_quickly(isolated_site, tmp_path):
    for path in ("/redir-badport", "/redir-badipv6"):
        start = time.monotonic()
        report = inspect(isolated_site, tmp_path / path[1:], paths=[path])
        assert time.monotonic() - start < 12
        checks = [c for c in report.checks if c.check_id == "NAVIGATION"]
        assert len(checks) == 2
        assert all(c.status == "BLOCKED" for c in checks), path
        assert "function takes exactly" not in str(report.to_dict())


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium opt-in")
def test_form_navigation_includes_one_navigation_row(isolated_site, tmp_path):
    report = inspect(isolated_site, tmp_path, paths=["/auto-post"])
    seen = [(c.viewport, c.check_id) for c in report.checks]
    assert len(seen) == len(set(seen))
    nav = [c for c in report.checks if c.check_id == "NAVIGATION"]
    writes = [c for c in report.checks if c.check_id == "MUTATING_REQUESTS_BLOCKED"]
    assert len(nav) == len(writes) == 2
    assert MalformedFixture.posts == 0
    assert all(c.status in ("WARN", "BLOCKED") for c in writes)


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium opt-in")
def test_404_is_fail_even_when_other_checks_blocked(isolated_site, tmp_path):
    report = inspect(isolated_site, tmp_path, paths=["/status404"])
    nav = [c for c in report.checks if c.check_id == "NAVIGATION"]
    assert len(nav) == 2
    assert all(c.status == "FAIL" for c in nav)
    assert report.to_dict()["counts"]["FAIL"] == 2


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium opt-in")
def test_blocked_analytics_does_not_invalidate_layout(isolated_site, tmp_path):
    report = inspect(isolated_site, tmp_path, paths=["/analytics"])
    layout = [c for c in report.checks if c.check_id == "HORIZONTAL_OVERFLOW"]
    assert len(layout) == 2
    assert all(c.status == "PASS" for c in layout)
    assert report.to_dict()["counts"]["BLOCKED"] == 0



@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium opt-in")
def test_browser_resolves_virtual_localhost_without_os_dns(isolated_site, tmp_path):
    # Chromium special-cases localhost subdomains; APIRequestContext uses the
    # OS resolver, which may not resolve app.localhost on Unix.
    url = isolated_site.replace("127.0.0.1", "app.localhost")
    report = inspect(url, tmp_path, paths=["/typo"])
    nav = [c for c in report.checks if c.check_id == "NAVIGATION"]
    assert len(nav) == 2
    assert all(c.status == "PASS" for c in nav), [
        (c.status, c.observed) for c in nav
    ]
