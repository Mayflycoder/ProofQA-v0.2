"""URL origin normalisation and a deliberately narrow Chromium proxy bypass."""

import pytest

from pqlqa.network import canonical_origin, restricted_chromium_args


def test_default_ports_are_equivalent():
    assert canonical_origin("http://localhost") == canonical_origin("http://localhost:80/")
    assert canonical_origin("https://example.com") == canonical_origin("https://example.com:443/")


def test_unicode_and_punycode_hosts_are_equivalent():
    assert canonical_origin("https://bücher.example/") == canonical_origin(
        "https://xn--bcher-kva.example/"
    )


def test_restricted_proxy_does_not_bypass_other_loopback_ports():
    args = restricted_chromium_args("http://127.0.0.1:9201/")
    assert "--proxy-server=http://127.0.0.1:9" in args
    bypass = next(arg for arg in args if arg.startswith("--proxy-bypass-list="))
    assert "<-loopback>" in bypass
    assert "127.0.0.1:9201" in bypass
    assert "127.0.0.1:9202" not in bypass
    assert "--force-webrtc-ip-handling-policy=disable_non_proxied_udp" in args


def test_invalid_origin_cannot_generate_bypass_list():
    for target in ("file:///etc/passwd", "http://", "about:blank"):
        with pytest.raises(ValueError):
            restricted_chromium_args(target)
