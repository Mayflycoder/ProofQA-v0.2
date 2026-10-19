import pytest

from pqlqa.models import Check, Report
from pqlqa.reporting import render_html, render_markdown, write_report
from pqlqa.safety import redact_url, safe_diagnostic, validate_paths, validate_target


def test_url_validation():
    assert validate_target("https://example.com/path") == "https://example.com/path"
    assert validate_target("http://127.0.0.1:8000") == "http://127.0.0.1:8000/"
    for url in (
        "file:///etc/passwd", "javascript:alert(1)", "https://user:secret@example.com",
        "https://example.com/?session=secret", "https://example.com/#abc",
        "https://example.com:99999/", "http://",
    ):
        with pytest.raises(ValueError):
            validate_target(url)


def test_report_never_renders_unescaped_observations(tmp_path):
    report = Report("QA-T1", "2026-10-18T10:00:00Z", "https://example.com/")
    report.checks.append(
        Check("TITLE", "mobile", "WARN", "Bad title", "Safe title", "<script>alert(1)</script>")
    )
    render = render_html(report)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in render
    assert "<script>alert(1)</script>" not in render
    write_report(report, tmp_path)
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.html").exists()
    assert (tmp_path / "report.md").exists()
    assert "&lt;script&gt;" in render_markdown(report)
    assert "<script>" not in render_markdown(report)
    assert report.to_dict()["counts"]["WARN"] == 1


def test_redacts_url_tokens():
    assert redact_url("https://user:pw@example.com/a?token=hi#ref") == "https://example.com/a"
    assert redact_url("https://example.com:8443/path?secret=1") == "https://example.com:8443/path"


def test_embedded_urls_and_common_secrets_redacted():
    original = (
        "Error reading https://user:pass@example.com/reset/F0OD?token=abc#frag "
        "with password=secretValue and api_key=key123"
    )
    safe = safe_diagnostic(original)
    assert "F0OD" not in safe and "user:pass" not in safe
    assert "abc" not in safe and "secretValue" not in safe
    assert "key123" not in safe and "[URL redacted]" in safe



def test_explicit_paths_have_a_strict_same_origin_budget():
    assert validate_paths(["/", "/about", "/about"]) == ["/", "/about"]
    for paths in (
        [], ["/"] * 9, ["//evil.example/x"], ["https://evil.example/"],
        ["/profile?token=123"], ["/file#section"], ["/../../secret"],
        ["/%2e%2e/admin"], ["relative"], ["/has space"],
    ):
        with pytest.raises(ValueError):
            validate_paths(paths)



def test_markdown_does_not_activate_attacker_markup():
    report = Report("QA-MD", "2026-10-18Z", "http://127.0.0.1/")
    hostile = "![beacon](//evil.example/collect) [sign in](https://evil.example/login)"
    report.checks.append(Check("JAVASCRIPT_ERRORS", "mobile", "WARN", "Untrusted", "", hostile))
    render = render_markdown(report)
    assert "![beacon](" not in render
    assert "[sign in](" not in render
    assert r"\!\[beacon\]\(" in render


def test_diagnostics_redact_bearer_json_cookie_and_protocol_relative_url():
    text = (
        'Authorization: Bearer abc.def.ghi "token": "JSONTOKEN123" '
        'cookie: sid=COOKIESECRET ![tracking](//example.test/collect)'
    )
    redacted = safe_diagnostic(text)
    assert "abc.def.ghi" not in redacted
    assert "JSONTOKEN123" not in redacted
    assert "COOKIESECRET" not in redacted
    assert "//example.test" not in redacted



def test_common_credentials_do_not_appear_in_saved_diagnostics():
    raw = (
        "Basic dXNlcjpTRUNSRVRQVw== "
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.SIGJWTSECRET "
        "AKIAIOSFODNN7EXAMPLE ghp_GITHUBTOKENSECRET0123456789abcdef "
        "sk_live_STRIPESECRET123 passwd=PASSWDSECRET "
        "-----BEGIN PRIVATE KEY-----MIIPRIVATESECRET "
        "postgres://admin:DBPASS@db/x"
    )
    safe = safe_diagnostic(raw)
    for marker in (
        "dXNlcjpTRUNSRVRQVw==", "SIGJWTSECRET",
        "AKIAIOSFODNN7EXAMPLE", "GITHUBTOKENSECRET", "STRIPESECRET",
        "PASSWDSECRET", "MIIPRIVATESECRET", "DBPASS",
    ):
        assert marker not in safe, f"Unredacted synthetic secret: {marker}"
