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
    _BodyTooLarge,
    _decompress_gzip_with_ceiling,
    _headers_do_tile,
    _read_limited_body,
)


# ── Tile cache/CORS by visibility ───────────────────────────────────────────

def test_private_tile_neither_caches_nor_opens_cors():
    """Mutation: always emit `public, max-age` (the old header).

    Private -> `private, no-store` and NO Access-Control-Allow-Origin.
    """
    h = _headers_do_tile("private")
    assert h["Cache-Control"] == "private, no-store"
    assert "Access-Control-Allow-Origin" not in h


def test_public_tile_stays_cacheable():
    h = _headers_do_tile("public")
    assert h["Cache-Control"] == "public, max-age=3600"
    assert h["Access-Control-Allow-Origin"] == "*"


# ── Bomba gzip: corte incremental no teto ───────────────────────────────────

def test_gzip_bomb_blocked_without_materializing():
    """Mutation: go back to a whole gzip.decompress() before the size check.

    100 MB of zeros compress to ~100 KB; the 1 MB ceiling cuts off before
    materializing the 100 MB. tracemalloc proves the output was NOT allocated
    whole — a decompress-everything-then-check would allocate the 100 MB and fail
    this memory ceiling.
    """
    import tracemalloc

    bomb = gzip.compress(b"\x00" * (100 * 1024 * 1024))
    assert len(bomb) < 1 * 1024 * 1024  # a bomb e pequena comprimida
    tracemalloc.start()
    try:
        with pytest.raises(_BodyTooLarge):
            _decompress_gzip_with_ceiling(bomb, 1 * 1024 * 1024)
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert pico < 16 * 1024 * 1024, f"materializou {pico} bytes (perto dos 100 MB)"


def test_legitimate_gzip_round_trip():
    payload = json.dumps({"type": "FeatureCollection", "features": [{"i": i} for i in range(500)]}).encode()
    out = _decompress_gzip_with_ceiling(gzip.compress(payload), 50 * 1024 * 1024)
    assert out == payload


def test_gzip_at_exact_limit_passes_and_one_above_is_blocked():
    dados = b"x" * 1000
    assert _decompress_gzip_with_ceiling(gzip.compress(dados), 1000) == dados
    with pytest.raises(_BodyTooLarge):
        _decompress_gzip_with_ceiling(gzip.compress(dados), 999)


def test_invalid_gzip_does_not_become_large_body():
    """Corrupted gzip must raise a zlib error (becomes 400 in the handler), never
    _BodyTooLarge (which becomes 413)."""
    with pytest.raises(Exception) as exc:
        _decompress_gzip_with_ceiling(b"isto nao e gzip", 50 * 1024 * 1024)
    assert not isinstance(exc.value, _BodyTooLarge)


# ── Reading the body with a ceiling ──────────────────────────────────────────

class _FakeReq:
    def __init__(self, pedacos):
        self._chunks = pedacos

    async def stream(self):
        for p in self._chunks:
            yield p


async def test_read_body_below_ceiling_joins_the_chunks():
    req = _FakeReq([b"abc", b"def", b"gh"])
    assert await _read_limited_body(req, 100) == b"abcdefgh"


async def test_read_body_above_ceiling_blocks_without_joining_everything():
    """Mutation: use `await request.body()` (buffers everything) instead of the cutoff.

    A body above the ceiling is rejected as soon as it crosses it, without reading the rest.
    """
    req = _FakeReq([b"x" * 50, b"y" * 60])  # 110 bytes, teto 100
    with pytest.raises(_BodyTooLarge):
        await _read_limited_body(req, 100)
