"""Regression for the portal exposure fixes (audit: high/medium).

- Tiles of a PRIVATE portal must not go out with `Cache-Control: public` nor
  `Access-Control-Allow-Origin: *`: the browser/CDN cache would serve the
  geometry after revocation, or to a request without a Bearer.
- The portal publish decompressed the WHOLE gzip before checking the ceiling: a
  bomb (a few KB -> GBs) would bring down the API through memory. Now it reads and
  decompresses with an incremental cutoff at the ceiling, off the event loop.

Each test fails WITHOUT the fix; the docstring names the mutation that breaks ONLY it.
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


# ── Tile cache/CORS by visibility ───────────────────────────────────────────

def test_tile_privado_nao_cacheia_nem_abre_cors():
    """Mutation: always emit `public, max-age` (the old header).

    Private -> `private, no-store` and NO Access-Control-Allow-Origin.
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
    """Mutation: go back to a whole gzip.decompress() before the size check.

    100 MB of zeros compress to ~100 KB; the 1 MB ceiling cuts off before
    materializing the 100 MB. tracemalloc proves the output was NOT allocated
    whole — a decompress-everything-then-check would allocate the 100 MB and fail
    this memory ceiling.
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
    """Corrupted gzip must raise a zlib error (becomes 400 in the handler), never
    _CorpoGrandeDemais (which becomes 413)."""
    with pytest.raises(Exception) as exc:
        _descomprimir_gzip_com_teto(b"isto nao e gzip", 50 * 1024 * 1024)
    assert not isinstance(exc.value, _CorpoGrandeDemais)


# ── Reading the body with a ceiling ──────────────────────────────────────────

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
    """Mutation: use `await request.body()` (buffers everything) instead of the cutoff.

    A body above the ceiling is rejected as soon as it crosses it, without reading the rest.
    """
    req = _ReqFalso([b"x" * 50, b"y" * 60])  # 110 bytes, teto 100
    with pytest.raises(_CorpoGrandeDemais):
        await _ler_corpo_limitado(req, 100)
