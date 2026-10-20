# ProofQA v0.2.0 — Local Developer Preview

ProofQA v0.2.0 is the first standalone public developer preview of the local-first, open-source browser QA engine.

## Included

- Local Python CLI (`proofqa`) with Playwright Chromium testing for up to eight explicitly selected same-origin pages.
- Desktop/mobile viewport checks, browser errors, page status, basic layout heuristics and automated axe-core accessibility checks.
- Evidence-backed PASS / FAIL / WARN / BLOCKED / NOT_VERIFIED outcomes, HTML/JSON/Markdown reports and local screenshots.
- Best-effort browser-level network restrictions, worker lifetime and termination coverage, and test fixtures for synthetic localhost pages.
- Python 3.12 GitHub Actions CI with lint, unit tests, real Chromium integration tests, a synthetic end-to-end scan, and downloadable test evidence.
- MIT license, security disclosure, contributor instructions and a platform threat model.

## Validation

The import pull request passed 42 automated tests on commit `0fe5595df73b2ae02476db97944da5ae266121d3`, including real Chromium integration tests. The synthetic two-page CLI scan generated HTML, JSON, Markdown and four screenshots, with 50 PASS, 2 WARN, 0 FAIL, 0 BLOCKED and 4 NOT_VERIFIED check outcomes.

This release is published only after the CI test job passes on the merge commit. Automated results are evidence for the tests run, **not** certification of every scenario or safety boundary.

## Important limitations

**Local-only:** Run only against pages you own or are explicitly authorized to test. Do not expose this CLI behind an internet-facing arbitrary-URL scanning endpoint.

This release is **not** a hosted SaaS platform, OS-isolated browser sandbox, SSRF-safe remote scanner, vulnerability scanner, penetration-testing tool, complete WCAG audit or medical/regulatory release certification. Browser-level network restrictions are best effort and are not a security boundary for untrusted remote users. Some third-party assets are intentionally blocked; visual completeness and worker WebSocket observations may be limited. Screenshots and reports can contain sensitive data and should be inspected before sharing.

## Install

See the repository README for setup and authorized local scanning examples. Python 3.11+ and a Playwright Chromium installation are required. For security, consult `SECURITY.md` and `docs/QA_PLATFORM_THREAT_MODEL.md` before extending the local runner into a hosted service.
