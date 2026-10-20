# Security and responsible disclosure

ProofQA is a **local developer preview**, not a hosted service, a network
sandbox, a vulnerability scanner, or a release-quality certification.

## Vulnerability reporting

Please do not publish exploit payloads, active credentials, private screenshots,
or customer data in a public GitHub issue. If GitHub private vulnerability
reporting is available for this repository, use that feature. Otherwise open
a general issue asking the maintainer to establish a private reporting channel
without including sensitive technical details.

Security reports are welcome when they include a minimal, synthetic local
reproducer. Do not test third-party websites without explicit authorization.

## Execution and privacy boundaries

- Run only on applications you own or are authorized to test, preferably
  staging with synthetic records. Misconfigured GET routes may mutate data.
- Chromium's proxy/bypass rules plus Playwright hooks are browser-level controls.
  They are **not OS-enforced egress isolation**, cannot guarantee the absence
  of data exfiltration on every browser version, and are inadequate for a SaaS
  service accepting public target URLs.
- Real sites may load cross-origin JavaScript, fonts and CSS. ProofQA blocks
  these by default; incomplete rendering invalidates some visual conclusions.
- Reports and screenshots remain local unless users manually share them.
  Review them for confidential information; automatic sanitization is
  incomplete, particularly for image pixels or unknown secret formats.
- No production credentials, real patient records, arbitrary code execution,
  remote SaaS scanning, penetration tests or security certifications are in
  scope for this preview.

See [the threat model](docs/QA_PLATFORM_THREAT_MODEL.md).
