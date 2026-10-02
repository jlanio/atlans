"""
Controle de acesso do portal em tiles e download.

Regressao: get_mvt_tile e download_portal_layer so checavam
`portal_access == "disabled"`. Um portal PRIVADO tinha as geometrias servidas
sem auth — bastava saber workflow_hash + layer_key (ou o UUID da camada), ambos
de baixa entropia. get_portal_data ja aplicava o gate completo; agora ele foi
extraido para enforce_portal_access e reaplicado nos tres endpoints.
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
async def test_portal_inexistente_404():
    with pytest.raises(HTTPException) as e:
        await enforce_portal_access(None, _req())
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_disabled_404():
    with pytest.raises(HTTPException) as e:
        await enforce_portal_access(_wf(access="disabled"), _req())
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_public_passa_sem_token():
    await enforce_portal_access(_wf(access="public"), _req())  # nao levanta


@pytest.mark.asyncio
async def test_private_sem_token_401():
    with pytest.raises(HTTPException) as e:
        await enforce_portal_access(_wf(access="private"), _req())
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_private_usuario_nao_autorizado_403():
    wf = _wf(access="private", shared=["alice"])
    with patch("app.core.utils.jwt_utils.decode_token",
               return_value={"type": "access", "sub": "bob", "username": "bob"}), \
            patch("app.core.utils.jwt_utils.is_token_blacklisted",
                  new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as e:
            await enforce_portal_access(wf, _req(auth="Bearer tok"))
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_private_usuario_autorizado_passa():
    wf = _wf(access="private", shared=["alice"])
    with patch("app.core.utils.jwt_utils.decode_token",
               return_value={"type": "access", "sub": "u-1", "username": "Alice"}), \
            patch("app.core.utils.jwt_utils.is_token_blacklisted",
                  new=AsyncMock(return_value=False)):
        await enforce_portal_access(wf, _req(auth="Bearer tok"))  # nao levanta (username case-insensitive)


@pytest.mark.asyncio
async def test_private_refresh_token_recusado():
    """Token que nao e de access (ex: refresh) nao vale no portal."""
    wf = _wf(access="private", shared=["alice"])
    with patch("app.core.utils.jwt_utils.decode_token",
               return_value={"type": "refresh", "sub": "u-1"}):
        with pytest.raises(HTTPException) as e:
            await enforce_portal_access(wf, _req(auth="Bearer tok"))
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_private_token_blacklistado_recusado():
    """Token revogado no logout nao acessa portal privado (defesa em profundidade)."""
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
async def test_download_endpoint_bloqueia_portal_privado(client):
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
            else:  # workflows — agora projeta as colunas do gate e le por .first()
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
async def test_tile_endpoint_bloqueia_portal_privado(client):
    """O tile resolve gate + camada numa consulta so, e o gate continua valendo.

    Cada pan/zoom pede dezenas de tiles; antes cada um fazia dois SELECTs de
    metadados (um deles carregando a `definition` inteira do fluxo) antes do
    ST_AsMVT. Agora e um outerjoin com as tres colunas que o gate le mais o
    layer_id — dai o duble responder por `.first()`, e nao por
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
