"""Explicit, machine-readable QA evidence contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

CheckStatus = Literal["PASS", "FAIL", "WARN", "BLOCKED", "NOT_VERIFIED"]


@dataclass(frozen=True)
class Check:
    check_id: str
    viewport: str
    status: CheckStatus
    finding: str
    expected: str
    observed: str
    evidence: str | None = None
    page_path: str = "/"


@dataclass
class Report:
    run_id: str
    created_at: str
    target: str
    final_urls: dict[str, str] = field(default_factory=dict)
    checks: list[Check] = field(default_factory=list)
    screenshots: dict[str, str] = field(default_factory=dict)
    pages: list[str] = field(default_factory=lambda: ["/"])
    scope: str = (
        "Authorized browser smoke checks of explicitly selected pages at two viewports, with "
        "non-safe HTTP methods blocked; browser WebSocket prevention best-effort; "
        "no sign-in, form submission, active security scan, workflow verification, "
        "automatic link crawling, load test, or regulatory assessment."
    )
    limitations: list[str] = field(default_factory=lambda: [
        "A PASS is evidence of the named check only, not proof of overall quality.",
        "The runner does not exercise business logic, authenticated flows, APIs or security",
        "controls.",
        "Browser timing and network conditions can affect results; manually confirm findings.",
        "Browser proxy and interception are NOT an operating-system network sandbox.",
        "External origins are blocked; layout and screenshots may not reflect the live site.",
        "JavaScript exception details are withheld from reports to avoid leaking secrets.",
        "Page scripts can still cause side effects via misused GET endpoints; staging only.",
        "Screenshots and errors stay local; inspect them for sensitive data before sharing.",
    ])

    def to_dict(self) -> dict:
        result = asdict(self)
        result["counts"] = {
            status: sum(check.status == status for check in self.checks)
            for status in ("PASS", "FAIL", "WARN", "BLOCKED", "NOT_VERIFIED")
        }
        return result
