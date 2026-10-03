"""
Tests for normalize_ows_endpoint_url (flow.utils.geo_helpers).

Goal: discard the query/fragment of OWS URLs (WFS/WMS/WMTS) pasted
by the user so they do not conflict with the params that the client (owslib,
httpx) injects when calling GetCapabilities/GetFeature.
"""
from __future__ import annotations

import pytest

from flow.utils.geo_helpers import normalize_ows_endpoint_url


class TestNormalizeOwsEndpointUrl:

    def test_full_url_with_query_string(self):
        raw = "https://geoservicos.inde.gov.br/geoserver/PGGM/ows?service=wms&version=1.3.0&request=GetCapabilities"
        assert normalize_ows_endpoint_url(raw) == "https://geoservicos.inde.gov.br/geoserver/PGGM/ows"

    def test_already_normalized_url_passes_intact(self):
        raw = "https://exemplo.com/geoserver/wfs"
        assert normalize_ows_endpoint_url(raw) == raw

    def test_remove_trailing_slash(self):
        assert normalize_ows_endpoint_url("https://exemplo.com/geoserver/wfs/") == \
            "https://exemplo.com/geoserver/wfs"

    def test_removes_multiple_trailing_slashes(self):
        assert normalize_ows_endpoint_url("https://exemplo.com/wfs///") == \
            "https://exemplo.com/wfs"

    def test_preserves_custom_port(self):
        raw = "https://localhost:8080/geoserver/ows?service=WFS"
        assert normalize_ows_endpoint_url(raw) == "https://localhost:8080/geoserver/ows"

    def test_remove_fragment(self):
        raw = "https://exemplo.com/wfs#camada-x"
        assert normalize_ows_endpoint_url(raw) == "https://exemplo.com/wfs"

    def test_query_and_fragment_together(self):
        raw = "https://exemplo.com/ows?service=WFS&version=2#hash"
        assert normalize_ows_endpoint_url(raw) == "https://exemplo.com/ows"

    def test_http_and_https_preserved(self):
        assert normalize_ows_endpoint_url("http://teste.com/wfs?a=1") == "http://teste.com/wfs"
        assert normalize_ows_endpoint_url("https://teste.com/wfs?a=1") == "https://teste.com/wfs"

    def test_url_with_host_only(self):
        # No path: scheme://host (with an empty path after rstrip)
        assert normalize_ows_endpoint_url("https://teste.com") == "https://teste.com"
        assert normalize_ows_endpoint_url("https://teste.com/") == "https://teste.com"

    def test_empty_string(self):
        assert normalize_ows_endpoint_url("") == ""

    def test_strip_whitespace(self):
        raw = "  https://exemplo.com/wfs?a=1  "
        assert normalize_ows_endpoint_url(raw) == "https://exemplo.com/wfs"

    def test_url_without_scheme_returns_original(self):
        # Without a scheme there is no way to parse — returns it for downstream validation.
        raw = "exemplo.com/wfs?a=1"
        result = normalize_ows_endpoint_url(raw)
        assert "exemplo.com" in result

    @pytest.mark.parametrize("invalid", [None, 0, [], {}])
    def test_invalid_types_return_empty_string(self, invalid):
        assert normalize_ows_endpoint_url(invalid) == ""

    def test_idempotence(self):
        """Aplicar duas vezes nao muda o resultado."""
        raw = "https://exemplo.com/wfs?a=1&b=2#frag"
        once = normalize_ows_endpoint_url(raw)
        twice = normalize_ows_endpoint_url(once)
        assert once == twice
