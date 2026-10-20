# Threat model — public QA testing platform

**Proposed architecture, not yet implemented.** Running untrusted websites or repository code for anonymous internet users is a security and cost-sensitive feature. The local runner is intentionally not remotely callable.

## Assets to protect

- Customer domains, repos, private issues, release metadata, credentials and logs.
- Other customers' projects, test history and screenshots.
- Runner network, cloud metadata service, environment variables, billing accounts and signing keys.
- Third-party websites that are not owned/authorized by the requesting user.

## Main abuse cases and mitigations

| Threat | Required guardrail before any hosted execution |
|---|---|
| SSRF / metadata API access through submitted URLs | Verify domain ownership; block IP literals for cloud scans, resolve & validate every connection and redirect, deny loopback/private/link-local/metadata addresses, constrain egress and DNS rebinding, cap redirects and bytes |
| Third-party site scanning without consent | Host ownership challenge and recorded authorization, staging-only defaults, conservative rate limits and takedown process |
| Executing malicious package/build scripts from uploaded repositories | **Do not run untrusted code in initial SaaS.** Later use short-lived locked-down containers, no privileges/tokens/internal access, restricted network and resource ceilings |
| Cross-tenant data exposure | Organization-scoped authorization on every project, job, artifact and issue endpoint, enforce with tests; private object storage and short-lived signed retrieval |
| Credential and token exposure | Avoid collecting production credentials; later use secret manager, scoped service accounts, redacted logs/traces, rotation and retention limits |
| Platform overload or denial of service | Verified signup, per-user/org quotas, bounded jobs, concurrency limits, browser timeouts and charge ceilings |
| Test runs mutate or damage customer environments | Read-only smoke checks by default; any synthetic data creation or destructive tests require separate explicit authorization and reset plan |
| False PASS / misleading regulatory endorsement | Per-check observed evidence and BLOCKED/NOT TESTED states; release-readiness never equals certified compliance |
| Prompts/screenshots contain malicious instructions | Treat customer content as untrusted data; no autonomous privileged agent tools driven by page text |
| Leak of customer data through report sharing | No public reports by default, scoped share links, retention/deletion, content redaction and human QA |

## Segregated future components

`Customer portal -> authenticated project and verified hostname -> bounded queue -> ephemeral isolated browser worker -> private report store -> authorized report viewer`

Only the job queue talks to browser workers. The public portal must **never** run Playwright jobs inline in a request handler. Browser workers must have no production credentials and no path to other customer projects. If source-code analysis is added, use read-only consented GitHub app scopes and do not check out/build arbitrary repositories in a privileged workflow.

## Explicit current limitations

Local developers themselves supply and authorize the URL on their own computer. The CLI has syntactic URL validation **not SSRF protection**: it is not acceptable to expose `inspect()` behind a public POST endpoint. No code execution, web crawling, authentication, active vulnerability scanning, penetration tests, load generation or regulatory validation are provided.

References:
- OWASP SSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- GitHub Actions secure use: https://docs.github.com/en/actions/reference/security/secure-use
- Playwright CI: https://playwright.dev/docs/ci
