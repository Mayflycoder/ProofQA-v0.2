"""Best-effort Chromium network containment for *local, authorized* scans.

A dead proxy plus a single explicit direct-bypass host:port blocks many browser
network paths that Playwright request interception cannot observe (WebSockets
from Workers, speculation, etc.). This is NOT an OS network firewall or SSRF
protection. Its behavior must be tested with real browser fixtures.
"""

from __future__ import annotations

from urllib.parse import urlsplit


def canonical_origin(value: str) -> tuple[str, str, int]:
    """Normalise scheme, IDN hostname and default port for origin comparison."""
    url = urlsplit(value)
    scheme = url.scheme.lower()
    if scheme not in ("http", "https") or not url.hostname:
        raise ValueError("Expected an HTTP(S) origin")
    hostname = url.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    port = url.port or (443 if scheme == "https" else 80)
    return scheme, hostname, port


def restricted_chromium_args(target: str) -> list[str]:
    """Deny all proxy traffic, permitting one direct target host:port.

    Chromium's implicit bypass for every loopback address must be explicitly
    subtracted. Otherwise a second loopback server would remain reachable.
    """
    _, host, port = canonical_origin(target)
    if ":" in host:
        host = f"[{host}]"
    return [
        "--proxy-server=http://127.0.0.1:9",
        f"--proxy-bypass-list=<-loopback>;{host}:{port}",
        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        "--disable-features=SpeculationRules,Prerender2",
    ]
