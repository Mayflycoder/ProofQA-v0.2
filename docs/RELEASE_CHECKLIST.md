# ProofQA v0.2 — release checklist

This is a local-only developer-preview checklist, not a hosted-scanner certification.

- [ ] CI on the clean public repository passes the Python and real Chromium suite.
- [ ] The sample CLI run writes HTML, JSON, Markdown and separate screenshots.
- [ ] The SIGHUP and SIGKILL tests pass on the release SHA without orphaned Chromium.
- [ ] Independent network probes and any blocked/unverified coverage are documented.
- [ ] Review the public branch for credentials, private documents and accidental customer artifacts.
- [ ] Verify license, security notice, README commands, package metadata and contributor instructions.
- [ ] Check the public diff contains no MedQMS or unrelated private repository history.
- [ ] Merge the reviewed PR to `main` only after the checks above pass.
- [ ] Tag `v0.2.0` and publish release notes with local-only limitations.

Release positioning: **ProofQA v0.2 — Local Developer Preview**.
