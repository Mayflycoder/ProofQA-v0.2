"""Adversarial egress regression: an authorized localhost origin, plus outside listeners.

Never use live/third-party targets. If Chromium's network flags are ignored on a
new browser version these tests MUST fail; route-only interception is insufficient.
"""

import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pqlqa.runner import inspect


class OriginFixture(BaseHTTPRequestHandler):
    outside = 0
    udp = 0

    def do_GET(self):
        host = "127.0.0.1"
        outside = type(self).outside
        udp = type(self).udp
        if self.path == "/ok":
            body = "<!doctype html><title>OK</title><h1>OK</h1>"
        elif self.path == "/worker-ws":
            body = (
                "<!doctype html><title>Worker</title><h1>Worker</h1>"
                "<script>new Worker(URL.createObjectURL(new Blob(["
                f"\"new WebSocket('ws://{host}:{outside}/ws-worker')\""
                "],{type:'text/javascript'})))</script>"
            )
        elif self.path == "/sharedworker-ws":
            body = (
                "<!doctype html><title>Shared worker</title><h1>Shared worker</h1>"
                "<script>new SharedWorker(URL.createObjectURL(new Blob(["
                f"\"new WebSocket('ws://{host}:{outside}/ws-shared')\""
                "],{type:'text/javascript'})))</script>"
            )
        elif self.path == "/webrtc":
            body = (
                "<!doctype html><title>WebRTC</title><h1>WebRTC</h1>"
                "<script>(async()=>{try{const pc=new RTCPeerConnection("
                f"{{iceServers:[{{urls:'stun:{host}:{udp}'}}]}});"
                "pc.createDataChannel('x');await pc.setLocalDescription("
                "await pc.createOffer());}catch(e){}})()</script>"
            )
        elif self.path == "/speculation":
            body = (
                "<!doctype html><title>Prefetch</title><h1>Prefetch</h1>"
                "<script type='speculationrules'>{\"prefetch\":["
                "{\"source\":\"list\",\"urls\":["
                f"\"http://{host}:{outside}/speculated\""
                "]}]}</script>"
            )
        elif self.path == "/popup":
            body = (
                "<!doctype html><title>Popup</title><h1>Popup</h1>"
                f"<script>window.open('http://{host}:{outside}/popup');"
                "window.open('/ok')</script>"
            )
        elif self.path == "/external-css":
            body = (
                "<!doctype html><title>CSS</title><h1>CSS</h1>"
                f"<link rel='stylesheet' href='http://{host}:{outside}/style.css'>"
                "<div style='width:1200px'>a wide div</div>"
            )
        else:
            self.send_response(404)
            self.end_headers()
            return
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


class OutsideFixture(BaseHTTPRequestHandler):
    hits: list[tuple[str, str]] = []

    def do_GET(self):
        type(self).hits.append((self.path, self.headers.get("Upgrade", "")))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"out-of-scope")

    def log_message(self, *_args):
        pass


@pytest.mark.skipif(os.getenv("PQL_QA_BROWSER_TEST") != "1", reason="Chromium fixture opt-in")
def test_browser_network_confines_worker_socket_webrtc_prefetch_and_popups(tmp_path):
    outside = ThreadingHTTPServer(("127.0.0.1", 0), OutsideFixture)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("127.0.0.1", 0))
    udp.settimeout(0.2)
    OriginFixture.outside = outside.server_port
    OriginFixture.udp = udp.getsockname()[1]
    target = ThreadingHTTPServer(("127.0.0.1", 0), OriginFixture)
    OutsideFixture.hits = []
    datagrams: list[bytes] = []
    stop = threading.Event()

    def recv_udp():
        while not stop.is_set():
            try:
                datagrams.append(udp.recvfrom(1024)[0])
            except socket.timeout:
                pass
            except OSError:
                break

    servers = [target, outside]
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in servers]
    threads.append(threading.Thread(target=recv_udp, daemon=True))
    for thread in threads:
        thread.start()
    try:
        url = f"http://127.0.0.1:{target.server_port}/"
        cases = (
            "/worker-ws", "/sharedworker-ws", "/webrtc",
            "/speculation", "/popup", "/external-css",
        )
        for case in cases:
            result = inspect(url, tmp_path / case.strip("/"), paths=[case])
            nav = [c for c in result.checks if c.check_id == "NAVIGATION"]
            assert len(nav) == 2
            assert all(c.status == "PASS" for c in nav), case
            if case == "/external-css":
                layout = [c for c in result.checks if c.check_id == "HORIZONTAL_OVERFLOW"]
                assert all(c.status == "BLOCKED" for c in layout)
        time.sleep(0.4)
        assert OutsideFixture.hits == [], OutsideFixture.hits
        assert not datagrams, f"WebRTC sent {len(datagrams)} UDP packets outside origin"
    finally:
        stop.set()
        udp.close()
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)
