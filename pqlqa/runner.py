"""Bounded, non-mutating HTTP checks for an explicitly authorized page URL."""

from __future__ import annotations

import os
import signal
import threading
import time
from collections.abc import Sequence
from dataclasses import asdict, replace
from datetime import datetime, timezone
from multiprocessing import get_context
from pathlib import Path
from queue import Empty
from urllib.parse import urljoin, urlsplit, urlunsplit
from uuid import uuid4

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from pqlqa.accessibility import audit_page
from pqlqa.models import Check, Report
from pqlqa.network import canonical_origin, restricted_chromium_args
from pqlqa.safety import redact_url, safe_diagnostic, validate_paths, validate_target

VIEWPORTS = {"desktop": (1365, 800), "mobile": (390, 844)}
VIEWPORT_TIMEOUT_SECONDS = 25
WORKER_WATCHDOG_GRACE_SECONDS = 4
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
DOWNSTREAM_CHECKS = {
    "PAGE_TITLE": ("Document title", "Nonempty document title"),
    "JAVASCRIPT_ERRORS": ("Uncaught JavaScript exceptions", "None on initial page load"),
    "NETWORK_FAILURES": ("Resource errors", "No failed or HTTP 4xx/5xx requests"),
    "MUTATING_REQUESTS_BLOCKED": (
        "Potentially mutating HTTP requests", "None attempted during page load"
    ),
    "WEBSOCKETS_BLOCKED": ("WebSocket connections", "None attempted during page load"),
    "OFF_ORIGIN_REQUESTS": ("Off-origin resource requests", "None attempted during page load"),
    "REDIRECTS_REFUSED": ("Redirects", "None attempted during page load"),
    "VIEWPORT_META": ("Viewport scaling metadata", "Responsive viewport metadata present"),
    "HORIZONTAL_OVERFLOW": ("Unexpected horizontal overflow", "No layout overflow"),
    "H1_PRESENT": ("Primary heading heuristic", "At least one <h1>"),
    "IMAGE_ALT": ("Image alt heuristic", "Images have alt attributes"),
    "A11Y_AUTOMATED": ("Automated axe accessibility rules", "No detectable axe rule violations"),
    "SCREENSHOT": ("Screenshot evidence", "Viewport screenshot saved locally"),
}


def _blocked_after_navigation(
    report: Report, viewport: str, reason: str, page_path: str = "/"
) -> None:
    for check_id, (finding, expected) in DOWNSTREAM_CHECKS.items():
        report.checks.append(Check(
            check_id=check_id, viewport=viewport, status="BLOCKED",
            finding=finding, expected=expected, observed=reason,
            page_path=page_path,
        ))


def _self_watch_worker(parent_pid: int, limit_seconds: int) -> None:
    """Terminate the detached Chromium group after parent death or deadline.

    This thread belongs to the viewport worker, not the CLI. The CLI cannot
    catch SIGKILL: a worker-local watchdog is essential to avoid orphaned
    Chromium processes when the CLI is killed or crashes.
    """
    deadline = time.monotonic() + limit_seconds
    worker_pid = os.getpid()
    while True:
        if os.getppid() != parent_pid or time.monotonic() >= deadline:
            # Never signal the test runner's/terminal's process group.
            if os.getpgrp() == worker_pid:
                os.killpg(worker_pid, signal.SIGKILL)
            os._exit(1)
        time.sleep(0.1)


def _viewport_worker(
    queue, target: str, output: str, name: str, width: int, height: int,
    browser_executable: str | None, expected_parent_pid: int, lifetime_seconds: int,
) -> None:
    """Own an isolated Chromium process so hostile pages cannot hang the parent."""
    # Group the browser worker with its Chromium/driver descendants on POSIX.
    if os.name == "posix":
        os.setsid()
        threading.Thread(
            target=_self_watch_worker,
            args=(expected_parent_pid, lifetime_seconds),
            name="proofqa-worker-watchdog",
            daemon=True,
        ).start()
    report = Report(run_id="WORKER", created_at="", target=target)
    try:
        with sync_playwright() as playwright:
            kwargs = {"headless": True, "args": restricted_chromium_args(target)}
            if browser_executable:
                kwargs["executable_path"] = browser_executable
            browser = playwright.chromium.launch(**kwargs)
            try:
                _check_viewport(browser, target, Path(output), report, name, width, height)
            finally:
                browser.close()
    except (PlaywrightError, OSError, TypeError, ValueError) as exc:
        # Prevent crash-after-navigation from manufacturing a second, contradictory
        # NAVIGATION row. Long Chromium launch logs contain private local paths.
        reason = safe_diagnostic(str(exc).splitlines()[0])
        report.checks.append(Check(
            check_id="WORKER_ERROR", viewport=name, status="BLOCKED",
            finding="Browser startup or inspection failed",
            expected="Chromium should finish the viewport inspection",
            observed=reason,
        ))
        emitted = {check.check_id for check in report.checks}
        if "NAVIGATION" not in emitted:
            report.checks.append(Check(
                check_id="NAVIGATION", viewport=name, status="BLOCKED",
                finding="Browser could not complete navigation",
                expected="Viewport navigation completes",
                observed="Browser worker interrupted",
            ))
        for check_id, (finding, expected) in DOWNSTREAM_CHECKS.items():
            if check_id not in emitted:
                report.checks.append(Check(
                    check_id=check_id, viewport=name, status="BLOCKED",
                    finding=finding, expected=expected,
                    observed="Browser worker interrupted before the check completed",
                ))
    queue.put({
        "checks": [asdict(check) for check in report.checks],
        "screenshots": report.screenshots,
        "final_urls": report.final_urls,
    })


def _stop_worker_tree(process) -> None:
    """Terminate a viewport worker and its Playwright/Chromium descendants."""
    pid = process.pid
    if pid is None:
        return
    if os.name == "posix":
        # The child calls setsid() before launching the driver. Never signal
        # the parent process group if SIGTERM arrives before child setsid().
        try:
            pgid = os.getpgid(pid)
        except ProcessLookupError:
            pgid = pid  # Child exited; grandchildren may retain the group.
        if pgid == pid and pgid != os.getpgrp():
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            process.join(0.3)
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    if process.is_alive():
        process.terminate()
        process.join(0.3)
    if process.is_alive():
        process.kill()
    process.join(0.5)


def _run_viewport(target, output, name, width, height, browser_executable):
    """Return bounded evidence and always clean owned browser descendants."""
    ctx = get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(
        target=_viewport_worker,
        args=(
            queue, target, str(output), name, width, height, browser_executable,
            os.getpid(), VIEWPORT_TIMEOUT_SECONDS + WORKER_WATCHDOG_GRACE_SECONDS,
        ),
    )
    try:
        process.start()
        process.join(VIEWPORT_TIMEOUT_SECONDS)
        if process.is_alive():
            reason = f"Browser viewport exceeded {VIEWPORT_TIMEOUT_SECONDS}s hard limit"
        elif process.exitcode != 0:
            reason = f"Browser worker exited unexpectedly (code {process.exitcode})"
        else:
            try:
                return queue.get(timeout=2)
            except Empty:
                reason = "Browser worker finished without returning evidence"
    except (OSError, RuntimeError, ValueError) as exc:
        reason = safe_diagnostic(str(exc).splitlines()[0])
    finally:
        # SIGTERM in the CLI raises a BaseException and unwinds through here.
        _stop_worker_tree(process)
        queue.close()
        queue.join_thread()
    blocked = Report(run_id="BLOCKED", created_at="", target=target)
    blocked.checks.append(Check(
        check_id="NAVIGATION", viewport=name, status="BLOCKED",
        finding="Browser worker could not complete",
        expected="A complete bounded viewport scan",
        observed=reason,
    ))
    _blocked_after_navigation(blocked, name, reason)
    return {
        "checks": [asdict(check) for check in blocked.checks],
        "screenshots": {},
        "final_urls": {},
    }


def inspect(
    url: str,
    output: Path,
    *,
    browser_executable: str | None = None,
    paths: Sequence[str] | None = None,
) -> Report:
    """Scan up to eight nominated paths, each viewport in a bounded worker process.

    Refuse nonempty output destinations so stale screenshots cannot be treated as
    evidence for a later run. Never recursively crawl. GETs can have side effects.
    """
    target = validate_target(url)
    parsed = urlsplit(target)
    selected_paths = validate_paths(
        paths if paths is not None else [parsed.path or "/"]
    )
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output directory must be empty; choose a fresh --output path")
    output.mkdir(parents=True, exist_ok=True)
    report = Report(
        run_id=f"QA-{uuid4().hex[:12].upper()}",
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        target=target,
        pages=selected_paths,
    )
    many = len(selected_paths) > 1
    for index, path in enumerate(selected_paths, start=1):
        absolute = urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
        prefix = f"page-{index:02d}/" if many else ""
        page_output = output / f"page-{index:02d}" if many else output
        page_output.mkdir(parents=True, exist_ok=True)
        for name, (width, height) in VIEWPORTS.items():
            data = _run_viewport(
                absolute, page_output, name, width, height, browser_executable
            )
            for item in data["checks"]:
                check = Check(**item)
                evidence = prefix + check.evidence if check.evidence else None
                report.checks.append(replace(check, page_path=path, evidence=evidence))
            for viewport, filename in data["screenshots"].items():
                key = f"{path} [{viewport}]" if many else viewport
                report.screenshots[key] = prefix + filename
            for viewport, final_url in data["final_urls"].items():
                key = f"{path} [{viewport}]" if many else viewport
                report.final_urls[key] = final_url
    return report


def _check_viewport(browser, target, output, report, name, width, height) -> None:
    context = browser.new_context(
        viewport={"width": width, "height": height},
        service_workers="block",
        is_mobile=name == "mobile",
        has_touch=name == "mobile",
        device_scale_factor=2 if name == "mobile" else 1,
    )
    blocked_writes: list[str] = []
    blocked_sockets: list[bool] = []
    blocked_navigations: list[str] = []
    off_origin_requests: list[str] = []
    refused_redirects: list[str] = []
    route_errors: list[str] = []
    origin = canonical_origin(target)

    def route_request(route) -> None:
        """Fetch without following redirects so browser redirects cannot bypass the route.

        A plain route.continue_() lets Chromium follow 30x responses below Playwright's
        routing callbacks, which can contact unauthorized destinations.
        """
        request = route.request
        try:
            same_origin = canonical_origin(request.url) == origin
        except (ValueError, UnicodeError):
            # Invalid URL or port on one resource must not poison the page.
            same_origin = False
        # Chromium has no Frame yet for popup navigation requests; inspecting
        # request.frame can raise. Never allow that to unwind the route handler.
        try:
            is_main = request.is_navigation_request() and request.frame == page.main_frame
        except PlaywrightError:
            is_main = False
        if not same_origin:
            if is_main:
                blocked_navigations.append("Off-origin main-frame navigation")
            else:
                off_origin_requests.append(request.resource_type)
            route.abort("blockedbyclient")
            return
        method = request.method.upper()
        if method not in SAFE_METHODS:
            blocked_writes.append(method)
            route.abort("blockedbyclient")
            return
        if request.resource_type != "document" or origin[1].endswith(".localhost"):
            # Browser-native loading handles streaming resources and special
            # *.localhost hostnames that the driver's OS resolver cannot see.
            # Its single-origin proxy rule still denies off-origin redirects.
            route.continue_()
            return
        try:
            # max_redirects=0 is essential: a browser-level continue_ or a normal
            # route.fetch() can contact a redirected destination before our guard.
            response = route.fetch(max_redirects=0, timeout=18000)
            if response.status in (301, 302, 303, 307, 308):
                location = response.headers.get("location") or ""
                try:
                    destination = urljoin(request.url, location)
                    redirect_allowed = canonical_origin(destination) == origin
                except (ValueError, UnicodeError):
                    redirect_allowed = False
                if redirect_allowed:
                    # Rebuild the response in-browser; Chromium can follow safe
                    # same-origin canonicalisation without issuing a new fetch
                    # from the privileged Playwright driver.
                    refused_redirects.append("followed same-origin redirect")
                    route.fulfill(response=response)
                    return
                refused_redirects.append("refused off-origin redirect")
                if is_main:
                    blocked_navigations.append(
                        "Cross-origin redirect refused by browser policy"
                    )
                route.abort("blockedbyclient")
                return
            route.fulfill(response=response)
        except (PlaywrightError, PlaywrightTimeout) as exc:
            route_errors.append(safe_diagnostic(str(exc)))
            try:
                route.abort("failed")
            except PlaywrightError:
                pass

    # Intercept before page creation. Deny external subresources, not just document
    # navigation. This is local-only best effort, NOT a browser egress firewall.
    context.route("**/*", route_request)

    def prevent_socket(ws) -> None:
        blocked_sockets.append(True)
        ws.close()

    context.route_web_socket("**/*", prevent_socket)
    # Block common window WebSocket attempts before page scripts run. This avoids
    # a Playwright WS-route deadlock on servers that never complete handshakes.
    # Dedicated workers and browser bugs still require the outer process watchdog.
    context.add_init_script("""(() => {
        const blocked = function () {
            console.warn("PROOFQA_WS_BLOCKED");
            throw new DOMException("WebSocket disabled for QA", "SecurityError");
        };
        Object.defineProperty(globalThis, "WebSocket", {
            value: blocked, writable: false, configurable: false
        });
    })();""")
    page = context.new_page()
    page.on(
        "console",
        lambda message: blocked_sockets.append(True)
        if message.text == "PROOFQA_WS_BLOCKED" else None,
    )
    errors: list[str] = []
    transport_failures: list[str] = []
    http_failures: list[str] = []
    page.on(
        "pageerror",
        lambda _error: errors.append("Uncaught JavaScript exception; text withheld"),
    )
    page.on(
        "requestfailed",
        lambda request: transport_failures.append("Request failed: [URL redacted]")
        if request.method.upper() in SAFE_METHODS else None,
    )
    page.on(
        "response",
        lambda response: http_failures.append(f"HTTP {response.status}")
        if response.status >= 400 else None,
    )
    try:
        response = page.goto(target, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(500)
    except (PlaywrightTimeout, PlaywrightError) as exc:
        report.checks.append(Check(
            check_id="NAVIGATION", viewport=name, status="BLOCKED",
            finding="Page could not be loaded", expected="Page is reachable within 20 seconds",
            observed=(
                "; ".join(blocked_navigations[:3])
                if blocked_navigations else (
                    "Main-document request was interrupted or exceeded 18 seconds"
                    if route_errors else safe_diagnostic(str(exc).splitlines()[0])
                )
            ),
        ))
        _blocked_after_navigation(report, name, "Navigation could not complete")
        context.close()
        return
    try:
        final_url = redact_url(page.url)
        try:
            off_origin = canonical_origin(page.url) != origin
        except (ValueError, UnicodeError):
            # chrome-error:// after a blocked form/meta navigation.
            off_origin = True
        if blocked_navigations or off_origin:
            report.checks.append(Check(
                check_id="NAVIGATION", viewport=name, status="BLOCKED",
                finding="Page tried to navigate outside the authorized origin",
                expected="Navigation remains on the specified origin",
                observed="Navigation outside authorized origin blocked; downstream checks skipped",
            ))
            return
        report.final_urls[name] = final_url
        status = response.status if response is not None else None
        report.checks.append(Check(
            check_id="NAVIGATION", viewport=name,
            status="PASS" if status is not None and 200 <= status < 400 else "FAIL",
            finding="Page HTTP response", expected="A successful HTTP response (200–399)",
            observed=f"HTTP {status}; final URL: {final_url}",
        ))
        if status is None or status >= 400:
            reason = f"Document returned HTTP {status}; dependent checks not executed"
            _blocked_after_navigation(report, name, reason)
            return
        title = page.title().strip()
        report.checks.append(Check(
            check_id="PAGE_TITLE", viewport=name, status="PASS" if title else "WARN",
            finding="Document title", expected="Nonempty document title",
            observed=(
                f"Nonempty document title ({len(title)} characters)"
                if title else "Missing or empty <title>"
            ),
        ))
        report.checks.append(Check(
            check_id="JAVASCRIPT_ERRORS", viewport=name,
            status="WARN" if errors else "PASS",
            finding="Uncaught JavaScript exceptions on initial page load",
            expected="No uncaught browser JavaScript exceptions",
            observed="; ".join(errors[:5]) if errors else "None observed",
        ))
        failures = transport_failures + http_failures
        report.checks.append(Check(
            check_id="NETWORK_FAILURES", viewport=name,
            status="WARN" if failures else "PASS",
            finding="Failed initial resource requests and HTTP errors",
            expected="No failed requests or HTTP 4xx/5xx responses",
            observed=(
                f"{len(failures)} issues"
                + (f": {', '.join(failures[:3])}" if failures else "")
            ),
        ))
        report.checks.append(Check(
            check_id="MUTATING_REQUESTS_BLOCKED", viewport=name,
            status="WARN" if blocked_writes else "PASS",
            finding="Potentially mutating HTTP requests intercepted",
            expected="No non-safe HTTP methods attempted during load",
            observed=f"Blocked {len(blocked_writes)} requests: {', '.join(blocked_writes[:8])}",
        ))
        report.checks.append(Check(
            check_id="WEBSOCKETS_BLOCKED", viewport=name,
            status="WARN" if blocked_sockets else "NOT_VERIFIED",
            finding="WebSocket interception observations are incomplete",
            expected="No outbound WebSockets; including worker contexts",
            observed=(
                f"{len(blocked_sockets)} window-level attempts observed; "
                "worker and SharedWorker socket attempts cannot be independently counted"
            ),
        ))
        report.checks.append(Check(
            check_id="OFF_ORIGIN_REQUESTS", viewport=name,
            status="WARN" if off_origin_requests else "PASS",
            finding="Off-origin resource requests refused",
            expected="No third-party requests attempted",
            observed=f"Blocked {len(off_origin_requests)} external resource requests",
        ))
        report.checks.append(Check(
            check_id="REDIRECTS_REFUSED", viewport=name,
            status=(
                "WARN" if any(item.startswith("refused") for item in refused_redirects)
                else "PASS"
            ),
            finding="HTTP redirect handling (legacy check ID)",
            expected="Safe same-origin redirects permitted; off-origin refused",
            observed="; ".join(refused_redirects[:5]) if refused_redirects else "None observed",
        ))
        report.checks.append(Check(
            check_id="VIEWPORT_META", viewport=name,
            status="PASS" if page.locator('meta[name="viewport"]').count() else "WARN",
            finding="Responsive viewport meta tag",
            expected='A <meta name="viewport"> tag is present',
            observed="Present" if page.locator('meta[name="viewport"]').count() else "Absent",
        ))
        metrics = page.evaluate("""() => ({
            width: document.documentElement.clientWidth,
            scrollWidth: document.documentElement.scrollWidth
        })""")
        if (
            not isinstance(metrics, dict)
            or type(metrics.get("width")) is not int
            or type(metrics.get("scrollWidth")) is not int
        ):
            raise ValueError("Invalid DOM geometry returned by the inspected page")
        overflow = metrics["scrollWidth"] - metrics["width"]
        report.checks.append(Check(
            check_id="HORIZONTAL_OVERFLOW", viewport=name,
            status=(
                "BLOCKED" if any(kind in ("stylesheet", "font")
                                 for kind in off_origin_requests)
                else ("FAIL" if overflow > 3 else "PASS")
            ),
            finding="Unexpected horizontal page overflow",
            expected="Document fits the current viewport within 3 px",
            observed=f"clientWidth={metrics['width']}, scrollWidth={metrics['scrollWidth']}",
        ))
        h1_count = page.locator("h1:visible").count()
        report.checks.append(Check(
            check_id="H1_PRESENT", viewport=name,
            status="PASS" if h1_count >= 1 else "WARN",
            finding="Page has a primary heading (heuristic)", expected="At least one <h1>",
            observed=f"{h1_count} elements",
        ))
        missing_alt = page.locator("img:not([alt])").count()
        report.checks.append(Check(
            check_id="IMAGE_ALT", viewport=name,
            status="WARN" if missing_alt else "PASS",
            finding="Images without alt attributes (heuristic)",
            expected="All image elements have an alt attribute, including decorative images",
            observed=f"{missing_alt} images without alt",
        ))
        report.checks.append(audit_page(page, name))
        filename = f"{name}.png"
        page.screenshot(path=str(output / filename), full_page=False, timeout=10000)
        report.screenshots[name] = filename
        report.checks.append(Check(
            check_id="SCREENSHOT", viewport=name, status="PASS",
            finding="Viewport screenshot evidence", expected="Screenshot saved locally",
            observed=f"Saved {filename}", evidence=filename,
        ))
    except (PlaywrightError, PlaywrightTimeout, TypeError, ValueError, KeyError) as exc:
        report.checks.append(Check(
            check_id="RENDERING", viewport=name, status="BLOCKED",
            finding="Render or screenshot operation failed",
            expected="Browser DOM and screenshot are available",
            observed=safe_diagnostic(str(exc)),
        ))
    finally:
        emitted = {c.check_id for c in report.checks if c.viewport == name}
        if "NAVIGATION" not in emitted:
            report.checks.append(Check(
                check_id="NAVIGATION", viewport=name, status="BLOCKED",
                finding="Page navigation interrupted",
                expected="Navigation remains on the specified origin",
                observed="A navigation failed before its status could be verified",
            ))
        for check_id, (finding, expected) in DOWNSTREAM_CHECKS.items():
            if check_id in emitted:
                continue
            attempted = {
                "MUTATING_REQUESTS_BLOCKED": blocked_writes,
                "WEBSOCKETS_BLOCKED": blocked_sockets,
                "OFF_ORIGIN_REQUESTS": off_origin_requests,
                "REDIRECTS_REFUSED": refused_redirects,
            }.get(check_id, [])
            report.checks.append(Check(
                check_id=check_id, viewport=name,
                status="WARN" if attempted else "BLOCKED",
                finding=finding, expected=expected,
                observed=(
                    f"Observed and blocked {len(attempted)} attempts before interruption"
                    if attempted else "Rendering could not complete this check"
                ),
            ))
        try:
            context.close()
        except PlaywrightError:
            # A browser crash must not unwind the parent worker and duplicate
            # already-observed results. WORKER_ERROR is added by the outer handler
            # only when errors escape earlier operations.
            pass
