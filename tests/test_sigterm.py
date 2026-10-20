"""A single-PID SIGTERM must clean the ProofQA viewport worker and Chromium.

The CLI subprocess is placed in its own process group *only for test cleanup*.
SIGTERM is deliberately delivered to the CLI PID alone, not to its group.
The CLI's stdout is a real file to avoid unrelated descendants keeping a pipe
open and causing subprocess.communicate() to hang in failure cleanup.
"""

import os
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class HungHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (
            b"<!doctype html><title>Hang</title><h1>Hang</h1>"
            b"<script>setTimeout(()=>{while(true){}},200)</script>"
        )
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


def _process_table():
    """Return pid, ppid, pgid, state, command without relying on command names."""
    out = subprocess.check_output(
        ["ps", "-eo", "pid=,ppid=,pgid=,stat=,args="], text=True
    )
    result = []
    for line in out.splitlines():
        fields = line.strip().split(None, 4)
        if len(fields) != 5:
            continue
        try:
            result.append((
                int(fields[0]), int(fields[1]), int(fields[2]),
                fields[3], fields[4],
            ))
        except ValueError:
            continue
    return result


def _kill_group(pgid):
    """Best-effort test-only cleanup of groups created by the test."""
    if pgid is None or pgid == os.getpgrp():
        return
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


@pytest.mark.skipif(
    os.getenv("PQL_QA_BROWSER_TEST") != "1" or not sys.platform.startswith("linux"),
    reason="Real-browser signal integration requires Linux CI",
)
@pytest.mark.parametrize("term_signal, expected_code", [
    (signal.SIGTERM, 143),
    (signal.SIGHUP, 129),
    (signal.SIGKILL, -9),
])
def test_single_pid_signal_cleans_worker_process_group(
    tmp_path, term_signal, expected_code,
):
    server = ThreadingHTTPServer(("127.0.0.1", 0), HungHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    log_path = tmp_path / "cli.log"
    worker_group = None
    observed_worker_groups = set()
    with log_path.open("w", encoding="utf-8") as output:
        cli = subprocess.Popen(
            [
                sys.executable, "-m", "pqlqa",
                "--url", f"http://127.0.0.1:{server.server_port}/",
                "--authorized", "--output", str(tmp_path / "result"),
            ],
            stdout=output, stderr=subprocess.STDOUT,
            # Isolate test cleanup from pytest's own process group.
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 15
            seen_children = []
            while time.monotonic() < deadline:
                seen_children = [
                    item for item in _process_table() if item[1] == cli.pid
                ]
                for pid, _ppid, pgid, state, _args in seen_children:
                    if pgid == pid and "Z" not in state:
                        observed_worker_groups.add(pgid)
                        worker_group = pgid
                        break
                if worker_group is not None or cli.poll() is not None:
                    break
                time.sleep(0.15)

            assert worker_group is not None, (
                f"No detached child group. CLI exit={cli.poll()}, "
                f"children={seen_children}; log={log_path.read_text()[:700]}"
            )
            # Deliver signal only to the CLI PID, not the process group.
            cli.send_signal(term_signal)
            code = cli.wait(timeout=12)
            assert code == expected_code, (
                f"CLI returned {code}: {log_path.read_text()[:700]}"
            )
            deadline = time.monotonic() + 5
            alive = []
            while time.monotonic() < deadline:
                alive = [
                    row for row in _process_table()
                    if row[2] == worker_group and not row[3].startswith("Z")
                ]
                if not alive:
                    break
                time.sleep(0.2)
            assert not alive, f"Worker/Chromium descendants still alive: {alive}"
        finally:
            if cli.poll() is None:
                cli.kill()
                cli.wait(timeout=5)
            # Clean any group seen during setup even when the test itself fails.
            for pgid in observed_worker_groups:
                _kill_group(pgid)
            _kill_group(cli.pid)
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
