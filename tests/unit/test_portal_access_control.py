"""
Portal access control for tiles and download.

Regression: get_mvt_tile and download_portal_layer only checked
`portal_access == "disabled"`. A PRIVATE portal had its geometries served
without auth — it was enough to know workflow_hash + layer_key (or the layer's
UUID), both low-entropy. get_portal_data already applied the full gate; now it
has been extracted into enforce_portal_access and reapplied in the three endpoints.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routers.portal_router import enforce_portal_access


def _wf(access="private", ative=True, shared=None):
    return MagicMock(portal_access=access, flag_ative=ative,
                     portal_shared_with=shared or [], id_hash="wf-1")


def _req(auth=None):
    r = MagicMock()
    r.headers = {"Authorization": auth} if auth else {}
    return r


# ── enforce_portal_access: o gate ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_portal_404():
    with pytest.raises(HTTPException) as e:
        await enforce_portal_access(None, _req())
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_disabled_404():
    with pytest.raises(HTTPException) as e:
        await enforce_portal_access(_wf(access="disabled"), _req())
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_public_passes_without_token():
    await enforce_portal_access(_wf(access="public"), _req())  # does not raise


@pytest.mark.asyncio
async def test_private_without_token_401():
    with pytest.raises(HTTPException) as e:
        await enforce_portal_access(_wf(access="private"), _req())
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_private_unauthorized_user_403():
    wf = _wf(access="private", shared=["alice"])
    with patch("app.core.utils.jwt_utils.decode_token",
               return_value={"type": "access", "sub": "bob", "username": "bob"}), \
            patch("app.core.utils.jwt_utils.is_token_blacklisted",
                  new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as e:
            await enforce_portal_access(wf, _req(auth="Bearer tok"))
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_private_authorized_user_passes():
    wf = _wf(access="private", shared=["alice"])
    with patch("app.core.utils.jwt_utils.decode_token",
               return_value={"type": "access", "sub": "u-1", "username": "Alice"}), \
            patch("app.core.utils.jwt_utils.is_token_blacklisted",
                  new=AsyncMock(return_value=False)):
        await enforce_portal_access(wf, _req(auth="Bearer tok"))  # does not raise (username case-insensitive)


@pytest.mark.asyncio
async def test_private_refresh_token_rejected():
    """A token that is not an access token (e.g. refresh) is not valid on the portal."""
    wf = _wf(access="private", shared=["alice"])
    with patch("app.core.utils.jwt_utils.decode_token",
               return_value={"type": "refresh", "sub": "u-1"}):
        with pytest.raises(HTTPException) as e:
            await enforce_portal_access(wf, _req(auth="Bearer tok"))
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_private_blacklisted_token_rejected():
    """A token revoked at logout cannot access a private portal (defense in depth)."""
    wf = _wf(access="private", shared=["u-1"])
    with patch("app.core.utils.jwt_utils.decode_token",
               return_value={"type": "access", "sub": "u-1", "username": "u-1"}), \
            patch("app.core.utils.jwt_utils.is_token_blacklisted",
                  new=AsyncMock(return_value=True)):
        with pytest.raises(HTTPException) as e:
            await enforce_portal_access(wf, _req(auth="Bearer tok"))
    assert e.value.status_code == 401


# ── Wiring: os endpoints chamam o gate ───────────────────────────────────────

@pytest.mark.asyncio
async def test_download_endpoint_blocks_private_portal(client):
    """download_portal_layer resolve o workflow dono e aplica o gate."""
    from app.main import app
    from app.api.dependencies import get_db

    async def _fake_db():
        db = MagicMock()

        async def _execute(stmt, *a, **k):
            sql = str(stmt).lower()
            res = MagicMock()
            if "portal_layers" in sql:
                res.scalar_one_or_none = MagicMock(
                    return_value=MagicMock(id_hash="layer-1", workflow_hash="wf-1",
                                           layer_key="camada", geojson_data={"x": 1}))
            else:  # workflows — now projects the gate's columns and reads via .first()
                res.first = MagicMock(return_value=_wf(access="private"))
            return res

        db.execute = AsyncMock(side_effect=_execute)
        yield db

    app.dependency_overrides[get_db] = _fake_db
    try:
        resp = await client.get("/artifacts/portal/layers/layer-1/download")
        assert resp.status_code == 401, "portal privado sem token deve dar 401"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_tile_endpoint_blocks_private_portal(client):
    """The tile resolves gate + layer in a single query, and the gate still holds.

    Each pan/zoom requests dozens of tiles; before, each one made two metadata
    SELECTs (one of them loading the workflow's whole `definition`) before
    ST_AsMVT. Now it is an outerjoin with the three columns the gate reads plus
    the layer_id — hence the double answers via `.first()`, and not via
    `.scalar_one_or_none()`.
    """
    from app.main import app
    from app.api.dependencies import get_db

    async def _fake_db():
        db = MagicMock()
        res = MagicMock()
        res.first = MagicMock(return_value=MagicMock(
            portal_access="private", flag_ative=True,
            portal_shared_with=[], layer_id=1,
        ))
        db.execute = AsyncMock(return_value=res)
        yield db

    app.dependency_overrides[get_db] = _fake_db
    try:
        resp = await client.get("/artifacts/tiles/wf-1/camada/10/1/1.pbf")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)
