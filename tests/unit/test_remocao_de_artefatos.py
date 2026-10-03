"""Removing an artifact is the same algorithm on all five paths.

The loop — local content becomes an order to the executor and the row only goes
once the order is DELIVERED; an object in MinIO goes first and a failure keeps
the row; the portal layer goes along; then the row — was written out in the
single DELETE, in the batch one, in the resend to a reconnecting executor, in
retention and in the workspace purge. The copies diverged: only the purge deleted
the portal layer of a delivered LOCAL artifact. On the other four paths the
artifact row vanished and the PortalLayer stayed — the published map stayed
online, serving from the database data the person had asked to delete (and that,
marked to stay on the executor, should not even have left it).

Real database (SQLite): what matters is what remains stored.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routers import artifacts_router
from app.core import artifact_cleanup
from app.core.authorization import workflow_access
from app.core.utils.datetime_utils import utc_now_naive
from app.models.artifact import Artifact
from app.models.base import Base
from app.models.portal_layer import PortalLayer

WS = "ws-1"


@asynccontextmanager
async def _from_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[Artifact.__table__, PortalLayer.__table__])
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def _published_local(SessionMaker, n: int = 1, *, vencido: bool = False):
    """A LOCAL artifact (bytes on the executor's disk) published to the portal."""
    async with SessionMaker() as db:
        db.add_all([
            Artifact(
                id_hash=f"art-{n}", workspace_id=WS, workflow_hash="wf-1", run_id="run-1",
                output_key=f"camada_{n}", filename=f"camada_{n}.geojson", size_bytes=700,
                content_location="executor", executor_id="exec-1",
                local_path=f"{WS}/run-1/camada_{n}.geojson", is_published=True,
                expires_at=utc_now_naive() - timedelta(days=1) if vencido else None,
            ),
            PortalLayer(workflow_hash="wf-1", layer_key=f"camada_{n}", geojson_data={"features": []}),
        ])
        await db.commit()


async def _leftover(SessionMaker) -> tuple[list[str], list[str]]:
    async with SessionMaker() as db:
        artefatos = (await db.execute(select(Artifact.id_hash))).scalars().all()
        camadas = (await db.execute(select(PortalLayer.layer_key))).scalars().all()
    return sorted(artefatos), sorted(camadas)


@pytest.fixture
def entrega(monkeypatch):
    """The executor receives the removal order (or not, with `entrega([])`)."""
    def instalar(ids=None):
        async def _ids_in_order(by_executor):
            todos = [i["_id"] for itens in by_executor.values() for i in itens]
            return todos if ids is None else [i for i in todos if i in ids]
        monkeypatch.setattr(artifact_cleanup, "_ordenar_remocao_local", _ids_in_order)
    instalar()
    return instalar


@pytest.fixture
def can_edit(monkeypatch):
    # Where `require_workspace_role` looks up the role (the comparison stays real).
    monkeypatch.setattr(workflow_access, "get_workspace_member_role", AsyncMock(return_value="owner"))


_WHO = SimpleNamespace(id_hash="u-1")


# ── The portal layer goes along with the delivered local artifact ────────────

@pytest.mark.asyncio
async def test_single_delete_of_local_artifact_removes_the_layer(entrega, can_edit):
    async with _from_db() as SessionMaker:
        await _published_local(SessionMaker)
        async with SessionMaker() as db:
            resposta = await artifacts_router.delete_artifact(
                "art-1", db=db, current_user=_WHO, workspace_ids=[WS],
            )

        assert resposta is None                        # 204, as before
        assert await _leftover(SessionMaker) == ([], [])


@pytest.mark.asyncio
async def test_batch_delete_of_local_artifact_removes_the_layer(entrega, can_edit):
    async with _from_db() as SessionMaker:
        await _published_local(SessionMaker, 1)
        await _published_local(SessionMaker, 2)
        pedido = SimpleNamespace(json=AsyncMock(return_value={"id_hashes": ["art-1", "art-2"]}))
        async with SessionMaker() as db:
            resposta = await artifacts_router.batch_delete_artifacts(
                pedido, db=db, current_user=_WHO, workspace_ids=[WS],
            )

        assert resposta == {"deleted": 2, "skipped": 0, "pendentes_no_executor": 0}
        assert await _leftover(SessionMaker) == ([], [])


@pytest.mark.asyncio
async def test_local_artifact_retention_removes_the_layer(entrega, monkeypatch):
    async with _from_db() as SessionMaker:
        await _published_local(SessionMaker, vencido=True)
        monkeypatch.setattr(artifact_cleanup, "AsyncSessionLocal", SessionMaker)

        assert await artifact_cleanup.purge_expired_artifacts() == 1
        assert await _leftover(SessionMaker) == ([], [])


@pytest.mark.asyncio
async def test_resend_to_reconnecting_executor_removes_the_layer(entrega, monkeypatch):
    async with _from_db() as SessionMaker:
        await _published_local(SessionMaker, vencido=True)
        monkeypatch.setattr(artifact_cleanup, "AsyncSessionLocal", SessionMaker)

        assert await artifact_cleanup.purgar_pendentes_do_executor("exec-1") == 1
        assert await _leftover(SessionMaker) == ([], [])


# ── The responses of each path did not change ────────────────────────────────

async def _published_in_minio(SessionMaker, n: int):
    async with SessionMaker() as db:
        db.add_all([
            Artifact(
                id_hash=f"art-{n}", workspace_id=WS, workflow_hash="wf-1", run_id="run-1",
                output_key=f"camada_{n}", filename=f"camada_{n}.geojson", size_bytes=100,
                s3_key=f"artifacts/{WS}/run-1/camada_{n}.geojson", is_published=True,
            ),
            PortalLayer(workflow_hash="wf-1", layer_key=f"camada_{n}", geojson_data={"features": []}),
        ])
        await db.commit()


@pytest.fixture
def minio(monkeypatch):
    """MinIO fails for the keys in `broken`."""
    broken: set[str] = set()

    def _delete_object(chave, allow_missing=True):
        if chave in broken:
            raise RuntimeError("MinIO fora")

    monkeypatch.setattr("app.core.storage.delete_strict", _delete_object)
    return broken


@pytest.mark.asyncio
async def test_single_delete_with_minio_down_is_502_and_nothing_is_removed(minio, can_edit):
    from fastapi import HTTPException

    async with _from_db() as SessionMaker:
        await _published_in_minio(SessionMaker, 1)
        minio.add(f"artifacts/{WS}/run-1/camada_1.geojson")
        async with SessionMaker() as db:
            with pytest.raises(HTTPException) as erro:
                await artifacts_router.delete_artifact("art-1", db=db, current_user=_WHO, workspace_ids=[WS])

        assert erro.value.status_code == 502
        assert await _leftover(SessionMaker) == (["art-1"], ["camada_1"])


@pytest.mark.asyncio
async def test_batch_counts_the_minio_failure_as_skipped(minio, can_edit):
    async with _from_db() as SessionMaker:
        await _published_in_minio(SessionMaker, 1)
        await _published_in_minio(SessionMaker, 2)
        minio.add(f"artifacts/{WS}/run-1/camada_2.geojson")
        pedido = SimpleNamespace(json=AsyncMock(return_value={"id_hashes": ["art-1", "art-2"]}))
        async with SessionMaker() as db:
            resposta = await artifacts_router.batch_delete_artifacts(
                pedido, db=db, current_user=_WHO, workspace_ids=[WS],
            )

        assert resposta == {"deleted": 1, "skipped": 1, "pendentes_no_executor": 0}
        # The failure keeps the row AND the layer: the next attempt finds both.
        assert await _leftover(SessionMaker) == (["art-2"], ["camada_2"])


@pytest.mark.asyncio
async def test_undelivered_order_keeps_artifact_and_layer(entrega, can_edit):
    """The layer only goes with the row: an offline executor leaves both."""
    entrega([])
    async with _from_db() as SessionMaker:
        await _published_local(SessionMaker)
        async with SessionMaker() as db:
            resposta = await artifacts_router.delete_artifact(
                "art-1", db=db, current_user=_WHO, workspace_ids=[WS],
            )

        assert resposta.status_code == 202
        assert await _leftover(SessionMaker) == (["art-1"], ["camada_1"])
