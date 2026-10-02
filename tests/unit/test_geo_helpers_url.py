"""
Testes de normalize_ows_endpoint_url (flow.utils.geo_helpers).

Objetivo: descartar query/fragment de URLs OWS (WFS/WMS/WMTS) coladas
pelo usuario para nao conflitar com os params que o cliente (owslib,
httpx) injeta na hora de chamar GetCapabilities/GetFeature.
"""
from __future__ import annotations

import pytest

from flow.utils.geo_helpers import normalize_ows_endpoint_url


class TestNormalizeOwsEndpointUrl:

    def test_url_completa_com_query_string(self):
        raw = "https://geoservicos.inde.gov.br/geoserver/PGGM/ows?service=wms&version=1.3.0&request=GetCapabilities"
        assert normalize_ows_endpoint_url(raw) == "https://geoservicos.inde.gov.br/geoserver/PGGM/ows"

    def test_url_ja_normalizada_passa_intacta(self):
        raw = "https://exemplo.com/geoserver/wfs"
        assert normalize_ows_endpoint_url(raw) == raw

    def test_remove_trailing_slash(self):
        assert normalize_ows_endpoint_url("https://exemplo.com/geoserver/wfs/") == \
            "https://exemplo.com/geoserver/wfs"

    def test_remove_multiplos_trailing_slashes(self):
        assert normalize_ows_endpoint_url("https://exemplo.com/wfs///") == \
            "https://exemplo.com/wfs"

    def test_preserva_porta_custom(self):
        raw = "https://localhost:8080/geoserver/ows?service=WFS"
        assert normalize_ows_endpoint_url(raw) == "https://localhost:8080/geoserver/ows"

    def test_remove_fragment(self):
        raw = "https://exemplo.com/wfs#camada-x"
        assert normalize_ows_endpoint_url(raw) == "https://exemplo.com/wfs"

    def test_query_e_fragment_juntos(self):
        raw = "https://exemplo.com/ows?service=WFS&version=2#hash"
        assert normalize_ows_endpoint_url(raw) == "https://exemplo.com/ows"

    def test_http_e_https_preservados(self):
        assert normalize_ows_endpoint_url("http://teste.com/wfs?a=1") == "http://teste.com/wfs"
        assert normalize_ows_endpoint_url("https://teste.com/wfs?a=1") == "https://teste.com/wfs"

    def test_url_so_com_host(self):
        # Sem path: scheme://host (com path vazio apos rstrip)
        assert normalize_ows_endpoint_url("https://teste.com") == "https://teste.com"
        assert normalize_ows_endpoint_url("https://teste.com/") == "https://teste.com"

    def test_string_vazia(self):
        assert normalize_ows_endpoint_url("") == ""

    def test_strip_whitespace(self):
        raw = "  https://exemplo.com/wfs?a=1  "
        assert normalize_ows_endpoint_url(raw) == "https://exemplo.com/wfs"

    def test_url_sem_scheme_devolve_original(self):
        # Sem scheme nao tem como parsear — devolve para validacao downstream.
        raw = "exemplo.com/wfs?a=1"
        result = normalize_ows_endpoint_url(raw)
        assert "exemplo.com" in result

    @pytest.mark.parametrize("invalid", [None, 0, [], {}])
    def test_tipos_invalidos_devolvem_string_vazia(self, invalid):
        assert normalize_ows_endpoint_url(invalid) == ""

    def test_idempotencia(self):
        """Aplicar duas vezes nao muda o resultado."""
        raw = "https://exemplo.com/wfs?a=1&b=2#frag"
        once = normalize_ows_endpoint_url(raw)
        twice = normalize_ows_endpoint_url(once)
        assert once == twice
