"""Remover um artefato é o mesmo algoritmo nos cinco caminhos.

O laço — conteúdo local vira ordem ao executor e a linha só cai com a ordem
ENTREGUE; objeto no MinIO sai primeiro e a falha preserva a linha; a camada do
portal sai junto; depois a linha — estava escrito no DELETE avulso, no lote, no
reenvio ao executor que reconecta, na retenção e na purga do workspace. As
cópias divergiram: só a purga apagava a camada do portal de um artefato LOCAL
entregue. Nos outros quatro caminhos a linha do artefato sumia e a PortalLayer
ficava — o mapa publicado continuava no ar, servindo do banco um dado que a
pessoa tinha mandado apagar (e que, marcado para ficar no executor, nem deveria
ter saído dele).

Banco de verdade (SQLite): o que importa é o que sobra gravado.
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
async def _banco():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[Artifact.__table__, PortalLayer.__table__])
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def _publicado_local(Sessao, n: int = 1, *, vencido: bool = False):
    """Um artefato LOCAL (bytes no disco do executor) publicado no portal."""
    async with Sessao() as db:
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


async def _sobrou(Sessao) -> tuple[list[str], list[str]]:
    async with Sessao() as db:
        artefatos = (await db.execute(select(Artifact.id_hash))).scalars().all()
        camadas = (await db.execute(select(PortalLayer.layer_key))).scalars().all()
    return sorted(artefatos), sorted(camadas)


@pytest.fixture
def entrega(monkeypatch):
    """O executor recebe a ordem de remoção (ou não, com `entrega([])`)."""
    def instalar(ids=None):
        async def _ordem(por_executor):
            todos = [i["_id"] for itens in por_executor.values() for i in itens]
            return todos if ids is None else [i for i in todos if i in ids]
        monkeypatch.setattr(artifact_cleanup, "_ordenar_remocao_local", _ordem)
    instalar()
    return instalar


@pytest.fixture
def pode_editar(monkeypatch):
    # Onde `exigir_papel_no_workspace` busca o papel (a comparação segue real).
    monkeypatch.setattr(workflow_access, "get_workspace_member_role", AsyncMock(return_value="owner"))


_QUEM = SimpleNamespace(id_hash="u-1")


# ── A camada do portal cai junto com o artefato local entregue ───────────────

@pytest.mark.asyncio
async def test_delete_avulso_de_artefato_local_apaga_a_camada(entrega, pode_editar):
    async with _banco() as Sessao:
        await _publicado_local(Sessao)
        async with Sessao() as db:
            resposta = await artifacts_router.delete_artifact(
                "art-1", db=db, current_user=_QUEM, workspace_ids=[WS],
            )

        assert resposta is None                        # 204, como antes
        assert await _sobrou(Sessao) == ([], [])


@pytest.mark.asyncio
async def test_delete_em_lote_de_artefato_local_apaga_a_camada(entrega, pode_editar):
    async with _banco() as Sessao:
        await _publicado_local(Sessao, 1)
        await _publicado_local(Sessao, 2)
        pedido = SimpleNamespace(json=AsyncMock(return_value={"id_hashes": ["art-1", "art-2"]}))
        async with Sessao() as db:
            resposta = await artifacts_router.batch_delete_artifacts(
                pedido, db=db, current_user=_QUEM, workspace_ids=[WS],
            )

        assert resposta == {"deleted": 2, "skipped": 0, "pendentes_no_executor": 0}
        assert await _sobrou(Sessao) == ([], [])


@pytest.mark.asyncio
async def test_retencao_de_artefato_local_apaga_a_camada(entrega, monkeypatch):
    async with _banco() as Sessao:
        await _publicado_local(Sessao, vencido=True)
        monkeypatch.setattr(artifact_cleanup, "AsyncSessionLocal", Sessao)

        assert await artifact_cleanup.purge_expired_artifacts() == 1
        assert await _sobrou(Sessao) == ([], [])


@pytest.mark.asyncio
async def test_reenvio_ao_executor_que_reconecta_apaga_a_camada(entrega, monkeypatch):
    async with _banco() as Sessao:
        await _publicado_local(Sessao, vencido=True)
        monkeypatch.setattr(artifact_cleanup, "AsyncSessionLocal", Sessao)

        assert await artifact_cleanup.purgar_pendentes_do_executor("exec-1") == 1
        assert await _sobrou(Sessao) == ([], [])


# ── As respostas de cada caminho não mudaram ─────────────────────────────────

async def _publicado_no_minio(Sessao, n: int):
    async with Sessao() as db:
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
    """O MinIO falha para as chaves de `quebradas`."""
    quebradas: set[str] = set()

    def _apagar(chave, allow_missing=True):
        if chave in quebradas:
            raise RuntimeError("MinIO fora")

    monkeypatch.setattr("app.core.storage.delete_strict", _apagar)
    return quebradas


@pytest.mark.asyncio
async def test_delete_avulso_com_o_minio_fora_e_502_e_nada_sai(minio, pode_editar):
    from fastapi import HTTPException

    async with _banco() as Sessao:
        await _publicado_no_minio(Sessao, 1)
        minio.add(f"artifacts/{WS}/run-1/camada_1.geojson")
        async with Sessao() as db:
            with pytest.raises(HTTPException) as erro:
                await artifacts_router.delete_artifact("art-1", db=db, current_user=_QUEM, workspace_ids=[WS])

        assert erro.value.status_code == 502
        assert await _sobrou(Sessao) == (["art-1"], ["camada_1"])


@pytest.mark.asyncio
async def test_lote_conta_a_falha_do_minio_como_skipped(minio, pode_editar):
    async with _banco() as Sessao:
        await _publicado_no_minio(Sessao, 1)
        await _publicado_no_minio(Sessao, 2)
        minio.add(f"artifacts/{WS}/run-1/camada_2.geojson")
        pedido = SimpleNamespace(json=AsyncMock(return_value={"id_hashes": ["art-1", "art-2"]}))
        async with Sessao() as db:
            resposta = await artifacts_router.batch_delete_artifacts(
                pedido, db=db, current_user=_QUEM, workspace_ids=[WS],
            )

        assert resposta == {"deleted": 1, "skipped": 1, "pendentes_no_executor": 0}
        # A falha preserva a linha E a camada: a próxima tentativa acha as duas.
        assert await _sobrou(Sessao) == (["art-2"], ["camada_2"])


@pytest.mark.asyncio
async def test_ordem_nao_entregue_mantem_artefato_e_camada(entrega, pode_editar):
    """A camada só sai com a linha: executor offline deixa os dois."""
    entrega([])
    async with _banco() as Sessao:
        await _publicado_local(Sessao)
        async with Sessao() as db:
            resposta = await artifacts_router.delete_artifact(
                "art-1", db=db, current_user=_QUEM, workspace_ids=[WS],
            )

        assert resposta.status_code == 202
        assert await _sobrou(Sessao) == (["art-1"], ["camada_1"])
