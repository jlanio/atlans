"""Regressao dos consertos de exposicao do portal (auditoria: altas/medias).

- Tiles de portal PRIVADO nao podem sair com `Cache-Control: public` nem
  `Access-Control-Allow-Origin: *`: o cache do browser/CDN serviria a geometria
  apos a revogacao, ou a uma requisicao sem Bearer.
- O publish do portal descomprimia o gzip INTEIRO antes de checar o teto: uma
  bomba (poucos KB -> GBs) derrubaria a API por memoria. Agora le e descomprime
  com corte incremental no teto, fora do event loop.

Cada teste falha SEM o fix; a docstring nomeia a mutacao que derruba SO ele.
"""
import gzip
import json

import pytest

from app.api.routers.portal_router import (
    _CorpoGrandeDemais,
    _descomprimir_gzip_com_teto,
    _headers_do_tile,
    _ler_corpo_limitado,
)


# ── Cache/CORS do tile por visibilidade ─────────────────────────────────────

def test_tile_privado_nao_cacheia_nem_abre_cors():
    """Mutacao: emitir sempre `public, max-age` (o header antigo).

    Privado -> `private, no-store` e SEM Access-Control-Allow-Origin.
    """
    h = _headers_do_tile("private")
    assert h["Cache-Control"] == "private, no-store"
    assert "Access-Control-Allow-Origin" not in h


def test_tile_publico_continua_cacheavel():
    h = _headers_do_tile("public")
    assert h["Cache-Control"] == "public, max-age=3600"
    assert h["Access-Control-Allow-Origin"] == "*"


# ── Bomba gzip: corte incremental no teto ───────────────────────────────────

def test_bomba_gzip_barrada_sem_materializar():
    """Mutacao: voltar a gzip.decompress() inteiro antes do check de tamanho.

    100 MB de zeros comprimem para ~100 KB; o teto de 1 MB corta antes de
    materializar os 100 MB. tracemalloc prova que a saida NAO foi alocada
    inteira — um decompress-inteiro-depois-checa alocaria os 100 MB e falharia
    este teto de memoria.
    """
    import tracemalloc

    bomba = gzip.compress(b"\x00" * (100 * 1024 * 1024))
    assert len(bomba) < 1 * 1024 * 1024  # a bomba e pequena comprimida
    tracemalloc.start()
    try:
        with pytest.raises(_CorpoGrandeDemais):
            _descomprimir_gzip_com_teto(bomba, 1 * 1024 * 1024)
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert pico < 16 * 1024 * 1024, f"materializou {pico} bytes (perto dos 100 MB)"


def test_gzip_legitimo_round_trip():
    payload = json.dumps({"type": "FeatureCollection", "features": [{"i": i} for i in range(500)]}).encode()
    out = _descomprimir_gzip_com_teto(gzip.compress(payload), 50 * 1024 * 1024)
    assert out == payload


def test_gzip_no_limite_exato_passa_e_uma_acima_barra():
    dados = b"x" * 1000
    assert _descomprimir_gzip_com_teto(gzip.compress(dados), 1000) == dados
    with pytest.raises(_CorpoGrandeDemais):
        _descomprimir_gzip_com_teto(gzip.compress(dados), 999)


def test_gzip_invalido_nao_vira_corpo_grande():
    """gzip corrompido deve levantar erro de zlib (vira 400 no handler), nunca
    _CorpoGrandeDemais (que vira 413)."""
    with pytest.raises(Exception) as exc:
        _descomprimir_gzip_com_teto(b"isto nao e gzip", 50 * 1024 * 1024)
    assert not isinstance(exc.value, _CorpoGrandeDemais)


# ── Leitura do corpo com teto ────────────────────────────────────────────────

class _ReqFalso:
    def __init__(self, pedacos):
        self._pedacos = pedacos

    async def stream(self):
        for p in self._pedacos:
            yield p


async def test_ler_corpo_abaixo_do_teto_junta_os_pedacos():
    req = _ReqFalso([b"abc", b"def", b"gh"])
    assert await _ler_corpo_limitado(req, 100) == b"abcdefgh"


async def test_ler_corpo_acima_do_teto_barra_sem_juntar_tudo():
    """Mutacao: usar `await request.body()` (bufferiza tudo) no lugar do corte.

    Um corpo acima do teto e recusado assim que passa, sem ler o resto.
    """
    req = _ReqFalso([b"x" * 50, b"y" * 60])  # 110 bytes, teto 100
    with pytest.raises(_CorpoGrandeDemais):
        await _ler_corpo_limitado(req, 100)
