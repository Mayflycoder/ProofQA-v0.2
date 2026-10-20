"""CLI safety and report exit-code contracts without browser or network access."""

import pytest

from pqlqa import cli
from pqlqa.models import Check, Report


def test_refuses_to_run_without_explicit_authorization(tmp_path):
    with pytest.raises(SystemExit) as err:
        cli.main(["--url", "https://example.com", "--output", str(tmp_path)])
    assert err.value.code == 2
    assert not list(tmp_path.iterdir())


def test_refuses_query_tokens_even_with_authorization(tmp_path):
    with pytest.raises(SystemExit) as err:
        cli.main([
            "--url", "https://example.com/?secret=leak", "--authorized",
            "--output", str(tmp_path),
        ])
    assert err.value.code == 2
    assert not list(tmp_path.iterdir())


def test_reports_failure_with_nonzero_exit(monkeypatch, tmp_path):
    report = Report("QA-UNIT", "2026-10-18T00:00:00Z", "https://example.com/")
    report.checks.append(Check(
        check_id="NAVIGATION", viewport="mobile", status="FAIL",
        finding="Unsuccessful HTTP status", expected="HTTP 200", observed="HTTP 404",
    ))
    monkeypatch.setattr(cli, "inspect", lambda *args, **kwargs: report)
    result = cli.main([
        "--url", "https://example.com", "--authorized", "--output", str(tmp_path),
    ])
    assert result == 1
    assert (tmp_path / "report.html").exists()
    assert (tmp_path / "report.json").exists()



def test_rejects_unsafe_or_unbounded_paths_before_launch(tmp_path):
    for extra in (["--path", "//evil.example"], ["--path", "/a?token=secret"]):
        with pytest.raises(SystemExit) as err:
            cli.main([
                "--url", "http://127.0.0.1:8000", "--authorized",
                "--output", str(tmp_path), *extra,
            ])
        assert err.value.code == 2
    assert not list(tmp_path.iterdir())



def test_output_destination_must_be_empty_without_deleting_old_files(tmp_path):
    dest = tmp_path / "old-results"
    dest.mkdir()
    previous = dest / "desktop.png"
    previous.write_bytes(b"old screenshot")
    with pytest.raises(SystemExit) as error:
        cli.main([
            "--url", "http://127.0.0.1:8877/", "--authorized",
            "--output", str(dest),
        ])
    assert error.value.code == 2
    assert previous.read_bytes() == b"old screenshot"



def test_warn_policy_is_opt_in_and_has_distinct_blocked_exit(monkeypatch, tmp_path):
    report = Report("QA-WARN", "2026-10-18Z", "https://example.com/")
    report.checks.append(Check("IMAGE_ALT", "desktop", "WARN", "alt", "present", "missing"))
    monkeypatch.setattr(cli, "inspect", lambda *a, **k: report)
    args = ["--url", "https://example.com", "--authorized"]
    assert cli.main([*args, "--output", str(tmp_path / "normal")]) == 0
    assert cli.main([*args, "--output", str(tmp_path / "strict"),
                     "--fail-on", "warn"]) == 1
    report.checks.append(Check("WEBSOCKETS_BLOCKED", "mobile", "BLOCKED",
                               "not completed", "complete", "blocked"))
    assert cli.main([*args, "--output", str(tmp_path / "blocked")]) == 3


def test_helpful_version_option(capsys):
    with pytest.raises(SystemExit) as result:
        cli.main(["--version"])
    assert result.value.code == 0
    assert "ProofQA 0.2.0" in capsys.readouterr().out



def test_real_fail_takes_priority_over_blocked_for_ci(monkeypatch, tmp_path):
    report = Report("QA-MIX", "2026-10-19Z", "https://example.com/")
    report.checks.extend([
        Check("NAVIGATION", "desktop", "FAIL", "Missing", "200", "404"),
        Check("IMAGE_ALT", "desktop", "BLOCKED", "Skipped", "checked", "unavailable"),
    ])
    monkeypatch.setattr(cli, "inspect", lambda *a, **k: report)
    assert cli.main([
        "--url", "https://example.com", "--authorized",
        "--output", str(tmp_path / "mixed"),
    ]) == 1


def test_not_verified_does_not_break_strict_warning_gate(monkeypatch, tmp_path):
    report = Report("QA-CLEAN", "2026-10-19Z", "https://example.com/")
    report.checks.extend([
        Check("NAVIGATION", "desktop", "PASS", "Loads", "200", "200"),
        Check("WEBSOCKETS_BLOCKED", "desktop", "NOT_VERIFIED",
              "Worker sockets", "None", "Not observable"),
    ])
    monkeypatch.setattr(cli, "inspect", lambda *a, **k: report)
    assert cli.main([
        "--url", "https://example.com", "--authorized",
        "--output", str(tmp_path / "clean"), "--fail-on", "warn",
    ]) == 0
    assert report.to_dict()["counts"]["NOT_VERIFIED"] == 1
