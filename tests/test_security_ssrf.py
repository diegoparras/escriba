"""Tests anti-SSRF: denylist de IPs internas + validación de URL (C2/M5).

Usa IPs LITERALES para no depender de DNS/red: getaddrinfo de una IP literal la
devuelve tal cual, así el test es hermético."""
import pytest

import app.security as sec


@pytest.mark.parametrize("ip", [
    "10.0.0.1", "192.168.1.1", "172.16.5.5",       # privadas RFC1918
    "127.0.0.1", "::1",                              # loopback (v4/v6)
    "169.254.169.254",                               # link-local = metadata de cloud
    "0.0.0.0",                                       # unspecified
    "224.0.0.1",                                     # multicast
])
def test_ip_blocked_internal(ip):
    assert sec._ip_is_blocked(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34", "2606:4700:4700::1111"])
def test_ip_allowed_public(ip):
    assert sec._ip_is_blocked(ip) is False


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/admin",
    "https://192.168.0.1/",
    "http://[::1]/",
    "ftp://example.com/x",       # esquema no permitido
    "file:///etc/passwd",
    "notaurl",
])
def test_assert_public_url_blocks(url):
    with pytest.raises(sec.SecurityError):
        sec.assert_public_url(url)


def test_assert_public_url_allows_public_ip():
    # IP pública literal: resuelve a sí misma, pasa, y devuelve la lista pinneable.
    assert sec.assert_public_url("http://8.8.8.8/") == ["8.8.8.8"]
