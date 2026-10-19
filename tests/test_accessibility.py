"""Tests for axe verdicts without requiring a browser."""

from types import SimpleNamespace

from pqlqa import accessibility


def test_accessibility_clean_page_is_scoped_pass(monkeypatch):
    fake = SimpleNamespace(run=lambda _page: SimpleNamespace(response={"violations": []}))
    monkeypatch.setattr(accessibility, "Axe", lambda: fake)
    result = accessibility.audit_page(object(), "desktop")
    assert result.status == "PASS"
    assert "manual" in result.observed


def test_accessibility_flags_violations_without_leaking_dom(monkeypatch):
    fake = SimpleNamespace(run=lambda _page: SimpleNamespace(response={
        "violations": [{
            "id": "image-alt",
            "impact": "critical",
            "nodes": [{"html": "<img src='/private/patient-info'>"}],
        }],
    }))
    monkeypatch.setattr(accessibility, "Axe", lambda: fake)
    result = accessibility.audit_page(object(), "mobile")
    assert result.status == "FAIL"
    assert "image-alt" in result.observed
    assert "private" not in result.observed


def test_accessibility_error_is_blocked_not_pass(monkeypatch):
    def fail(_page):
        raise RuntimeError("Error at https://host.dev/secret?token=TOPSECRET")

    monkeypatch.setattr(accessibility, "Axe", lambda: SimpleNamespace(run=fail))
    result = accessibility.audit_page(object(), "mobile")
    assert result.status == "BLOCKED"
    assert "TOPSECRET" not in result.observed
