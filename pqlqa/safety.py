"""Input policy. This is a local runner, not a hosted arbitrary-URL scanner."""

from __future__ import annotations

import re
from collections.abc import Sequence
from urllib.parse import urlsplit, urlunsplit

_URL_IN_TEXT = re.compile(r"(?i)(?:https?|wss?)://[^\s\"'<>]+")
_POSSIBLE_SECRET = re.compile(
    r"""(?i)(["']?(?:token|password|secret|session|cookie|authorization|"""
    r"""passwd|pwd|db[_-]?password|"""
    r"""api[_-]?key|access[_-]?token|refresh[_-]?token)["']?\s*[:=]\s*)"""
    r"""(?:"[^"]*"|'[^']*'|[^\s,;]+)"""
)
_BEARER_SECRET = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_PROTOCOL_RELATIVE = re.compile(r"""(?i)(?<!:)(?<!/)//[A-Za-z0-9.\[\]:_-]+/[^\s"'<>)]*""")
_NONHTTP_CREDENTIAL_URI = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s\"'<>]+")
_JWT_SECRET = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_BASIC_SECRET = re.compile(r"(?i)\bBasic\s+[A-Za-z0-9+/]{8,}={0,2}")
_AWS_KEY = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
_GITHUB_TOKEN = re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{10,}\b")
_STRIPE_TOKEN = re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9_]{8,}\b")
_PEM_BLOCK = re.compile(
    r"(?is)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?"
    r"(?:-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\Z)"
)


def validate_target(value: str) -> str:
    """Accept only an explicit HTTP(S) page URL without embedded credentials or tokens.

    IMPORTANT: This is not SSRF protection and must never be reused as a sufficient
    authorization control in a public service. A future cloud runner needs independently
    verified target ownership, egress restrictions, redirect/DNS validation and quotas.
    """
    raw = value.strip()
    try:
        url = urlsplit(raw)
        port = url.port  # Detect malformed port ranges.
    except ValueError as exc:
        raise ValueError("Invalid target URL") from exc
    if url.scheme not in ("http", "https") or not url.hostname:
        raise ValueError("Target must be a complete HTTP or HTTPS URL")
    if url.username is not None or url.password is not None:
        raise ValueError("Do not embed credentials in the target URL")
    if url.query or url.fragment:
        raise ValueError("Remove query parameters and fragments (they may contain secrets)")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Invalid target port")
    return urlunsplit((url.scheme, url.netloc, url.path or "/", "", ""))


def redact_url(value: str) -> str:
    """Discard URL credentials, query strings and fragments from saved reports."""
    try:
        url = urlsplit(value)
        host = url.hostname or "unknown"
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        if url.port is not None:
            host = f"{host}:{url.port}"
        return urlunsplit((url.scheme, host, url.path or "/", "", ""))
    except ValueError:
        return "[unavailable]"


def safe_diagnostic(value: str) -> str:
    """Redact *whole* embedded URLs and common credential-like values in diagnostics.

    This is defense in depth, not a guarantee: arbitrary exception text may include
    other sensitive content. Reports remain local-only and must be reviewed before sharing.
    """
    result = str(value)
    result = _PEM_BLOCK.sub("[PRIVATE KEY redacted]", result)
    result = _URL_IN_TEXT.sub("[URL redacted]", result)
    result = _NONHTTP_CREDENTIAL_URI.sub("[URL redacted]", result)
    result = _PROTOCOL_RELATIVE.sub("[URL redacted]", result)
    result = _BEARER_SECRET.sub("Bearer [REDACTED]", result)
    result = _BASIC_SECRET.sub("Basic [REDACTED]", result)
    for pattern in (_JWT_SECRET, _AWS_KEY, _GITHUB_TOKEN, _STRIPE_TOKEN):
        result = pattern.sub("[CREDENTIAL redacted]", result)
    return _POSSIBLE_SECRET.sub(lambda m: f"{m.group(1)}[REDACTED]", result)[:400]



_SIMPLE_PATH = re.compile(r"^/[A-Za-z0-9_./~-]*$")


def validate_paths(paths: Sequence[str]) -> list[str]:
    """Bound and validate explicit same-origin page paths; never accept URLs.

    The conservative initial syntax excludes queries, encoded slashes, fragments and
    unicode paths. A later iteration may add more complete URL-path handling.
    """
    if isinstance(paths, (str, bytes)) or not 1 <= len(paths) <= 8:
        raise ValueError("Specify between 1 and 8 page paths using --path")
    selected: list[str] = []
    for path in paths:
        if (
            not isinstance(path, str)
            or len(path) > 256
            or not _SIMPLE_PATH.fullmatch(path)
            or path.startswith("//")
            or any(segment in (".", "..") for segment in path.split("/"))
        ):
            raise ValueError("Paths must be simple same-origin paths like / or /about")
        if path not in selected:
            selected.append(path)
    return selected
