"""Opt-in real Chromium checks against isolated loopback-only fixtures."""

import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pqlqa.reporting import write_report
from pqlqa.runner import inspect


class FixtureHandler(BaseHTTPRequestHandler):
    writes_received = 0
    outside_port = None

    def do_POST(self):
        type(self).writes_received += 1
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path == "/redirect-local":
            self.send_response(302)
            self.send_header(
                "Location", f"http://127.0.0.1:{type(self).outside_port}/landing"
            )
            self.end_headers()
            return
        if self.path == "/websocket-outside":
            body = (
                "<!doctype html><title>WebSocket</title><h1>Socket</h1>"
                f"<script>try{{new WebSocket('ws://127.0.0.1:{type(self).outside_port}/ws')}}"
                "catch(e){}</script>"
            ).encode("utf-8")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/external-resources":
            body = (
                "<!doctype html><title>External fixture</title><h1>Example</h1>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                f"<img alt='fixture' src='http://127.0.0.1:{type(self).outside_port}/image.png'>"
                f"<script>fetch('http://127.0.0.1:{type(self).outside_port}/secret?key=XYZ')"
                ".catch(()=>{});</script>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/hang":
            body = (
                "<!doctype html><title>Hang</title><h1>Hang</h1>"
                "<script>setTimeout(()=>{while(true){}},200)</script>"
            ).encode("utf-8")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/tamper-metrics":
            body = (
                "<!doctype html><title>tampered</title><h1>Title</h1>"
                "<script>Object.defineProperty(document.documentElement,'clientWidth',"
                "{get:()=> 'not-a-number'})</script>"
            ).encode("utf-8")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/tamper-heuristics":
            body = (
                "<!doctype html><title>tampered</title><p>No H1</p><img src='/ok.png'>"
                "<script>const q=Document.prototype.querySelectorAll;"
                "Document.prototype.querySelectorAll=function(s){"
                "return s==='h1'?[1]:q.call(this,s)};"
                "Object.defineProperty(document,'images',{get:()=>[]})</script>"
            ).encode("utf-8")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "https://example.com/private")
            self.end_headers()
            return
        if self.path == "/missing.js":
            self.send_response(404)
            self.end_headers()
            return
        if self.path == "/abort":
            self.connection.close()
            return
        content = (
            "<!doctype html><title>Local smoke-test fixture</title>"
            "<h1>QA example page</h1>"
            "<div style='width:1200px;height:1px'>wide</div>"
            "<script src='/missing.js'></script>"
            "<script>fetch('/mutate',{method:'POST',body:'synthetic test'})"
            ".catch(()=>{}); setTimeout(()=>{throw new Error("
            "'Failed at https://user:pw@example.com/reset/secret?token=SECRET123')},30)"
            "</script>"
        ).encode("utf8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *_args):
        return


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium integration opt-in")
def test_real_browser_finds_mobile_overflow_and_js_exception(tmp_path):
    FixtureHandler.writes_received = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report = inspect(
            f"http://127.0.0.1:{server.server_port}/", tmp_path,
            browser_executable=os.getenv("PQL_CHROMIUM_EXECUTABLE") or None,
        )
        checks = {(c.viewport, c.check_id): c.status for c in report.checks}
        blocked_by_environment = any(
            c.status == "BLOCKED" and "ERR_BLOCKED_BY_ADMINISTRATOR" in c.observed
            for c in report.checks
        )
        if blocked_by_environment and os.getenv("PQL_QA_ALLOW_LOCAL_NETWORK_SKIP") == "1":
            pytest.skip("This execution environment blocks loopback browser navigation")
        assert checks["mobile", "NAVIGATION"] == "PASS"
        assert checks["mobile", "HORIZONTAL_OVERFLOW"] == "FAIL"
        assert checks["mobile", "JAVASCRIPT_ERRORS"] == "WARN"
        assert checks["mobile", "NETWORK_FAILURES"] == "WARN"
        assert checks["mobile", "MUTATING_REQUESTS_BLOCKED"] == "WARN"
        assert checks["desktop", "PAGE_TITLE"] == "PASS"
        assert checks["desktop", "A11Y_AUTOMATED"] in ("PASS", "FAIL")
        assert FixtureHandler.writes_received == 0
        assert "SECRET123" not in str(report.to_dict())
        assert "user:pw" not in str(report.to_dict())
        write_report(report, tmp_path)
        assert (tmp_path / "report.json").exists()
        assert (tmp_path / "mobile.png").exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium integration opt-in")
def test_navigation_failure_reports_all_downstream_checks_as_blocked(tmp_path):
    from pqlqa.runner import DOWNSTREAM_CHECKS

    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report = inspect(
            f"http://127.0.0.1:{server.server_port}/abort", tmp_path,
            browser_executable=os.getenv("PQL_CHROMIUM_EXECUTABLE") or None,
        )
        blocked_by_environment = any(
            "ERR_BLOCKED_BY_ADMINISTRATOR" in c.observed for c in report.checks
        )
        if blocked_by_environment and os.getenv("PQL_QA_ALLOW_LOCAL_NETWORK_SKIP") == "1":
            pytest.skip("This execution environment blocks loopback browser navigation")
        for viewport in ("desktop", "mobile"):
            checks = {c.check_id: c.status for c in report.checks if c.viewport == viewport}
            assert checks["NAVIGATION"] == "BLOCKED"
            assert all(checks[id_] == "BLOCKED" for id_ in DOWNSTREAM_CHECKS)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)



@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium integration opt-in")
def test_two_explicit_pages_are_separate_in_reports(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report = inspect(
            f"http://127.0.0.1:{server.server_port}/",
            tmp_path,
            paths=["/", "/docs"],
            browser_executable=os.getenv("PQL_CHROMIUM_EXECUTABLE") or None,
        )
        blocked_by_environment = any(
            "ERR_BLOCKED_BY_ADMINISTRATOR" in c.observed for c in report.checks
        )
        if blocked_by_environment and os.getenv("PQL_QA_ALLOW_LOCAL_NETWORK_SKIP") == "1":
            pytest.skip("This execution environment blocks loopback browser navigation")
        assert report.pages == ["/", "/docs"]
        assert {(c.page_path, c.viewport) for c in report.checks
                if c.check_id == "NAVIGATION"} == {
            ("/", "desktop"), ("/", "mobile"),
            ("/docs", "desktop"), ("/docs", "mobile"),
        }
        assert report.screenshots["/ [desktop]"] == "page-01/desktop.png"
        assert report.screenshots["/docs [mobile]"] == "page-02/mobile.png"
        assert (tmp_path / "page-01" / "desktop.png").exists()
        assert (tmp_path / "page-02" / "mobile.png").exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)



@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium integration opt-in")
def test_cross_origin_redirect_is_blocked(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report = inspect(
            f"http://127.0.0.1:{server.server_port}/redirect",
            tmp_path,
            browser_executable=os.getenv("PQL_CHROMIUM_EXECUTABLE") or None,
        )
        blocked_by_environment = any(
            "ERR_BLOCKED_BY_ADMINISTRATOR" in c.observed for c in report.checks
        )
        if blocked_by_environment and os.getenv("PQL_QA_ALLOW_LOCAL_NETWORK_SKIP") == "1":
            pytest.skip("This execution environment blocks loopback browser navigation")
        for viewport in ("desktop", "mobile"):
            nav = next(c for c in report.checks
                       if c.check_id == "NAVIGATION" and c.viewport == viewport)
            assert nav.status == "BLOCKED"
            assert "redirect refused" in nav.observed
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)



class ExternalHandler(BaseHTTPRequestHandler):
    hits: list[str] = []

    def do_GET(self):
        type(self).hits.append(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"external fixture")

    def log_message(self, *_args):
        return


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium integration opt-in")
def test_redirect_and_external_resources_never_reach_outside_origin(tmp_path):
    outside = ThreadingHTTPServer(("127.0.0.1", 0), ExternalHandler)
    ExternalHandler.hits = []
    FixtureHandler.outside_port = outside.server_port
    target = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    threads = []
    for server in (outside, target):
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        threads.append(thread)
    try:
        url = f"http://127.0.0.1:{target.server_port}/"
        redirect = inspect(url, tmp_path / "redirect", paths=["/redirect-local"])
        assert all(
            c.status == "BLOCKED" for c in redirect.checks
            if c.check_id == "NAVIGATION"
        )
        report = inspect(url, tmp_path / "resources", paths=["/external-resources"])
        statuses = {(c.viewport, c.check_id): c.status for c in report.checks}
        assert statuses["desktop", "NAVIGATION"] == "PASS"
        assert statuses["mobile", "NAVIGATION"] == "PASS"
        assert statuses["desktop", "OFF_ORIGIN_REQUESTS"] == "WARN"
        assert statuses["mobile", "OFF_ORIGIN_REQUESTS"] == "WARN"
        sockets = inspect(url, tmp_path / "sockets", paths=["/websocket-outside"])
        ws_checks = [c for c in sockets.checks if c.check_id == "WEBSOCKETS_BLOCKED"]
        assert len(ws_checks) == 2
        assert all(c.status == "WARN" for c in ws_checks)
        assert ExternalHandler.hits == [], "Off-origin browser requests escaped confinement"
    finally:
        for server in (target, outside):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium integration opt-in")
def test_untrusted_dom_monkeypatch_cannot_forge_heading_or_crash_report(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/"
        bad = inspect(url, tmp_path / "crash", paths=["/tamper-metrics"])
        assert all(
            c.status == "BLOCKED" for c in bad.checks
            if c.check_id == "HORIZONTAL_OVERFLOW"
        )
        fake = inspect(url, tmp_path / "fake", paths=["/tamper-heuristics"])
        result = {(c.viewport, c.check_id): c.status for c in fake.checks}
        assert result["desktop", "H1_PRESENT"] == "WARN"
        assert result["mobile", "IMAGE_ALT"] == "WARN"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)



@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium integration opt-in")
def test_hung_page_becomes_bounded_blocked_report(tmp_path, monkeypatch):
    import time

    import pqlqa.runner as runner

    monkeypatch.setattr(runner, "VIEWPORT_TIMEOUT_SECONDS", 4)
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        started = time.monotonic()
        report = inspect(
            f"http://127.0.0.1:{server.server_port}/hang",
            tmp_path,
        )
        assert time.monotonic() - started < 15
        statuses = [c.status for c in report.checks if c.check_id == "NAVIGATION"]
        assert statuses == ["BLOCKED", "BLOCKED"]
        write_report(report, tmp_path)
        assert (tmp_path / "report.json").exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
