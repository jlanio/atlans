"""Regression of the validate_url_ssrf hardening (audit SEG-81)."""
import ipaddress
import pytest

from flow.utils.geo_helpers import _dangerous_address, validate_url_ssrf


@pytest.mark.parametrize("ip", [
    "169.254.169.254",   # cloud metadata (link-local)
    "127.0.0.1", "10.0.0.5", "192.168.1.1", "172.16.0.1",
    "100.64.0.1",         # CGNAT (SEG-81)
    "0.0.0.0",            # unspecified
    "::1",                # loopback IPv6
    "::ffff:169.254.169.254",  # IPv4-mapped em IPv6
])
def test_dangerous_addresses(ip):
    assert _dangerous_address(ipaddress.ip_address(ip)) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34"])
def test_public_addresses_ok(ip):
    assert _dangerous_address(ipaddress.ip_address(ip)) is False


def test_internal_literal_ip_is_rejected_not_swallowed():
    # Before, the raise from the literal-IP block fell into the `except ValueError`
    # and was swallowed; now it refuses directly.
    with pytest.raises(ValueError):
        validate_url_ssrf("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(ValueError):
        validate_url_ssrf("http://100.64.0.1/")


def test_invalid_scheme():
    with pytest.raises(ValueError):
        validate_url_ssrf("file:///etc/passwd")
