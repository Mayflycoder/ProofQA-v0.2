"""Axe-powered accessibility check with minimized evidence output.

Automated testing detects only a subset of accessibility defects.
Only rule IDs, severity and affected-element counts leave the browser;
raw DOM snippets and user-entered values are deliberately not copied.
"""

from __future__ import annotations

from axe_playwright_python.sync_playwright import Axe

from pqlqa.models import Check
from pqlqa.safety import safe_diagnostic


def audit_page(page, viewport: str) -> Check:
    """Return PASS/FAIL/BLOCKED for axe rule detection on the rendered page."""
    finding = "Automated accessibility rule checks (axe-core)"
    expected = "No violations detected by automated axe rules on this rendered page"
    try:
        result = Axe().run(page)
        violations = result.response["violations"]
    except Exception as exc:
        return Check(
            check_id="A11Y_AUTOMATED",
            viewport=viewport,
            status="BLOCKED",
            finding=finding,
            expected=expected,
            observed=f"Accessibility engine could not finish: {safe_diagnostic(str(exc))}",
        )
    if not violations:
        observed = "No automated violations detected; manual accessibility testing is still needed"
        status = "PASS"
    else:
        details = [
            f"{rule.get('id', 'unknown')} ({rule.get('impact', 'unknown')}): "
            f"{len(rule.get('nodes', []))} affected elements"
            for rule in violations[:8]
        ]
        observed = f"{len(violations)} rule violations: " + "; ".join(details)
        if len(violations) > 8:
            observed += f"; and {len(violations) - 8} more"
        status = "FAIL"
    return Check(
        check_id="A11Y_AUTOMATED",
        viewport=viewport,
        status=status,
        finding=finding,
        expected=expected,
        observed=observed,
    )
