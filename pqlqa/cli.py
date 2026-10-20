"""Local QA runner CLI. No server-side user URL fetching or source execution."""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

from pqlqa import __version__
from pqlqa.reporting import write_report
from pqlqa.runner import inspect
from pqlqa.safety import validate_paths, validate_target


class _SignalTermination(BaseException):
    """Unwind the active viewport so its process tree is cleaned."""

    def __init__(self, signum: int) -> None:
        self.signum = signum


def _terminate_handler(signum, _frame) -> None:
    raise _SignalTermination(signum)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run read-only smoke checks on a web application "
            "you own or are authorized to test"
        )
    )
    parser.add_argument("--version", action="version", version=f"ProofQA {__version__}")
    parser.add_argument(
        "--fail-on", choices=("fail", "warn"), default="fail",
        help="Exit nonzero for FAIL (default) or WARN and FAIL",
    )
    parser.add_argument(
        "--url", required=True, help="Target page URL (no credentials or query tokens)"
    )
    parser.add_argument(
        "--authorized", action="store_true", help="Confirm you may test this target"
    )
    parser.add_argument("--output", type=Path, default=Path("./qa-results"))
    parser.add_argument(
        "--path", action="append", dest="paths",
        help="Explicit same-origin path to test, e.g. /about (repeat up to eight times)",
    )
    parser.add_argument("--chromium-path", default=None, help="Optional local Chromium executable")
    args = parser.parse_args(argv)
    if not args.authorized:
        parser.error("Explicit authorization is required: pass --authorized for your own app")
    try:
        target = validate_target(args.url)
        paths = validate_paths(args.paths or [urlsplit(target).path or "/"])
    except ValueError as exc:
        parser.error(str(exc))
    # SIGTERM sent to only the CLI PID must not orphan its Chromium descendants.
    can_handle_signal = threading.current_thread() is threading.main_thread()
    handled_signals = (signal.SIGTERM, signal.SIGHUP) if hasattr(signal, "SIGHUP") else (
        signal.SIGTERM,
    )
    prior_handlers = {}
    if can_handle_signal:
        for signum in handled_signals:
            prior_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, _terminate_handler)
    try:
        report = inspect(
            target, args.output, browser_executable=args.chromium_path, paths=paths,
        )
    except _SignalTermination as exc:
        print("ProofQA terminated; active browser worker cleaned", file=sys.stderr)
        return 128 + exc.signum
    except KeyboardInterrupt:
        print("ProofQA interrupted; active browser worker cleaned", file=sys.stderr)
        return 130
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    finally:
        if can_handle_signal:
            for signum, previous in prior_handlers.items():
                signal.signal(signum, previous)
    write_report(report, args.output)
    counts = report.to_dict()["counts"]
    print(f"Run {report.run_id}: {counts}. Report: {(args.output / 'report.html').resolve()}")
    if counts["FAIL"]:
        return 1
    if counts["BLOCKED"]:
        return 3
    if args.fail_on == "warn" and counts["WARN"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
