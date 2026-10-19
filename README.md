# ProofQA v0.2

**Open-source, local-first browser QA with evidence you can inspect.**

ProofQA runs a bounded set of Chromium checks against **pages you own or are explicitly authorized to test**. It records what it checked, what it observed, what failed, and what it **could not verify**. No signup, cloud account, or paid AI API is required.

**Status: local developer preview.** ProofQA is not a hosted URL scanner, vulnerability scanner, release certification, full WCAG audit, or regulatory compliance tool.

## Quick start

Prerequisites: Python 3.11+ and a supported installation of Playwright Chromium.

```bash
git clone https://github.com/Mayflycoder/ProofQA-v0.2.git
cd ProofQA-v0.2
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m playwright install chromium
```

On Windows PowerShell, replace activation with `.venv\Scripts\Activate.ps1`.

Run the scanner against **your own running local website**, using a fresh output directory:

```bash
proofqa --url http://127.0.0.1:3000 --authorized --path / --path /about --output ./proofqa-results
```

Change the URL and paths to your own site. If your site runs at a different port, specify it. ProofQA accepts up to eight explicitly named, same-origin paths and does not crawl your site.

Open `proofqa-results/report.html` to inspect findings and screenshots. The same scan also writes `report.json` and `report.md` for tooling and issue trackers. A destination must be new or empty so screenshots cannot be mixed across runs.

## What ProofQA checks

| Area | Included in v0.2 |
| --- | --- |
| Navigation | HTTP status per selected page, desktop and mobile |
| Browser runtime | Uncaught JavaScript exceptions, resource failures and HTTP errors |
| Layout | Horizontal overflow heuristic, responsive viewport metadata |
| Accessibility | Automated axe-core rules, heading presence and image-alt heuristics |
| Safety signals | Attempted non-safe HTTP methods, off-origin requests, redirects and observed WebSocket use |
| Evidence | Viewport screenshots; structured PASS / FAIL / WARN / BLOCKED / NOT_VERIFIED verdicts |

Automated accessibility scans cover only detectable rule violations. **They do not establish WCAG conformance**. Responsive findings may be incomplete when the page depends on third-party stylesheets or fonts that ProofQA refuses to load.

## CI results and exit codes

```bash
ruff check .
pytest -q
PQL_QA_BROWSER_TEST=1 pytest -q tests
proofqa --help
```

The browser integration tests require installed Chromium and use *synthetic localhost fixtures only*. The repository's GitHub Actions workflow runs them using Python 3.12 and archives synthetic example reports.

| Exit code | Meaning |
| --- | --- |
| 0 | No FAIL or BLOCKED checks (WARN is permitted by default) |
| 1 | FAIL exists, or WARN exists with `--fail-on warn` |
| 2 | Invalid invocation or unusable output directory |
| 3 | BLOCKED checks without a FAIL |

`NOT_VERIFIED` identifies an explicit coverage limitation; it is not evidence that the corresponding behavior passed. A returned PASS applies only to that check, on that page and viewport.

## Privacy and limitations

- Only run against applications you own or are authorized to test, preferably staging with synthetic data. Improperly implemented GET endpoints can have side effects.
- ProofQA blocks cross-origin browser requests using Chromium-level proxy settings and Playwright hooks; **this is not OS-level network isolation or SSRF prevention**.
- The tool blocks third-party resources by default. This may reduce page fidelity and cause some visual checks to be BLOCKED rather than treated as website defects.
- Browser WebSockets in Workers and SharedWorkers are not completely observable; the report distinguishes unverified behavior from passing checks.
- Screenshots can contain private application data. All artifacts stay local by default; inspect them before sharing.
- Login journeys, form submission, active security testing, load testing, authenticated business workflows, full mobile-device simulation and release certification are **out of scope**.

Read [SECURITY.md](SECURITY.md) and the [threat model](docs/QA_PLATFORM_THREAT_MODEL.md) before extending this runner into a hosted service.

## Contributing

Bug reports and focused pull requests are welcome. Please include a synthetic repro and verification steps. See [CONTRIBUTING.md](CONTRIBUTING.md) and [MIT License](LICENSE).
