# Contributing to ProofQA

Thank you for helping make developer QA more transparent and accessible.

## Before contributing

- Use synthetic pages and localhost fixtures; do not scan a third-party domain as part of the automated tests.
- Open an issue describing the problem and proposed acceptance evidence for larger changes.
- Keep PASS, FAIL, WARN, BLOCKED and NOT_VERIFIED distinguishable; never present untested functionality as verified.
- Do not add production credentials, screenshots containing real personal information, private customer artifacts, or telemetry by default.

## Developer setup

See [README.md](README.md) for local setup, then run:

~~~bash
# From the repository root
ruff check .
pytest -q
~~~

For integration testing, install Playwright Chromium and run the loopback-only fixture tests with **PQL_QA_BROWSER_TEST=1**.

Contributions should include a focused test and a concise explanation of the user-visible behavior. Security reports should avoid posting secrets or exploit details in public issues. Do not merge or publish until independent review confirms the stated scope.
