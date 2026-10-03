# tests/unit/test_artifact_service.py
"""
Artifact listing as a service — the door both transports use.

This file exists because of a measurement: with `verify_workspace_access`
deleted from the service, the whole suite stayed green. The only tenant test
there was covered the path WITHOUT `workspace_id`, where what holds the line is
`in_(workspace_ids)`; the path WITH the parameter — the only one that receives a
value from the client — had none. And that is the one the REST route exposes
directly from the query string.

What is tested here is the service, not the tool: the tool has its own door
(`resolver_workspace`) and would block before getting here, masking the absence
of this one. The route has nothing besides this.
"""
from __future__ import annotations


import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.services.artifact_service import listar_artefatos
from tests.unit._mcp_harness import TABELAS, criar_artefato

WS_1 = "11111111-1111-4111-8111-111111111111"
WS_2 = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
async def banco():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield fabrica
    finally:
        await engine.dispose()


# ── A porta ──────────────────────────────────────────────────────────────────


async def test_pedir_workspace_fora_da_lista_recusa(banco):
    """The measured regression: without this guard, `GET /artifacts?workspace_id=<alheio>`
    returned the neighbor's collection, and no test failed."""
    async with banco() as db:
        await criar_artefato(db, run_id="r2", workspace_id=WS_2, filename="alheia.geojson")

        with pytest.raises(HTTPException) as exc:
            await listar_artefatos(db, [WS_1], workspace_id=WS_2)

    assert exc.value.status_code == 403


async def test_o_parametro_estreita_o_escopo_nunca_o_amplia(banco):
    """Asking for a workspace that IS in the list still works, and only that one."""
    async with banco() as db:
        await criar_artefato(db, run_id="r1", workspace_id=WS_1, filename="minha.geojson")
        await criar_artefato(db, run_id="r2", workspace_id=WS_2, filename="alheia.geojson")

        pagina = await listar_artefatos(db, [WS_1, WS_2], workspace_id=WS_1)

    assert pagina["total"] == 1
    assert pagina["items"][0]["filename"] == "minha.geojson"


async def test_sem_parametro_o_corte_e_a_lista_inteira_do_chamador(banco):
    async with banco() as db:
        await criar_artefato(db, run_id="r1", workspace_id=WS_1)
        await criar_artefato(db, run_id="r2", workspace_id=WS_2)

        pagina = await listar_artefatos(db, [WS_1])

    assert pagina["total"] == 1


async def test_lista_vazia_de_workspaces_nao_vira_todos(banco):
    """`in_([])` has to mean "nothing", not "no filter"."""
    async with banco() as db:
        await criar_artefato(db, run_id="r1", workspace_id=WS_1)

        pagina = await listar_artefatos(db, [])

    assert pagina["total"] == 0


# ── A busca ──────────────────────────────────────────────────────────────────


async def test_curinga_do_usuario_e_literal_e_nao_varre_tudo(banco):
    """The other escape test looks at the SQL, not the TERM — and the term is what matters.

    `test_artifacts_busca_por_workflow.py` asserts that the word `ESCAPE` appears
    in the rendered SQL, which pins the `escape="\\\\"` of the `ilike`. What it does
    NOT pin is the transformation of `a_b` into `a\\_b`: deleting that line, that
    test keeps passing and `_` becomes a wildcard again — searching for `_` starts
    returning the whole collection, exactly what the docstring over there promises
    does not happen.

    Here the proof is behavioral, against the database: of the two rows, only the
    one with the LITERAL underscore may come back.
    """
    async with banco() as db:
        # `aXb` matches the PATTERN `a_b` if `_` is a wildcard, and does not if it is
        # literal. It is the row that discriminates — without it, both versions of
        # the code return the same thing and the test proves nothing.
        await criar_artefato(db, run_id="r1", workspace_id=WS_1, filename="aXb.geojson")
        await criar_artefato(db, run_id="r2", workspace_id=WS_1, filename="a_b.geojson")

        pagina = await listar_artefatos(db, [WS_1], search="a_b")

    assert pagina["total"] == 1, "o sublinhado voltou a ser curinga"
    assert pagina["items"][0]["filename"] == "a_b.geojson"


async def test_porcento_do_usuario_tambem_e_literal(banco):
    async with banco() as db:
        # `100X` matches `100%` with `%` as a wildcard; only `100%` matches literally.
        await criar_artefato(db, run_id="r1", workspace_id=WS_1, filename="100X.geojson")
        await criar_artefato(db, run_id="r2", workspace_id=WS_1, filename="100%.geojson")

        pagina = await listar_artefatos(db, [WS_1], search="100%")

    assert pagina["total"] == 1, "o porcento voltou a ser curinga"
    assert pagina["items"][0]["filename"] == "100%.geojson"


# ── The storage key does not leak into REST ──────────────────────────────────


async def test_a_chave_do_storage_so_sai_sob_pedido(banco):
    """`incluir_chave` exists so that the extraction does not widen the screen's contract.

    MCP needs the `s3_key` to decide whether there is an object to sign; the
    interface does not. Without a guard, a future refactor would return it to
    everyone and nobody would notice — the response would just be "a bigger field".
    """
    async with banco() as db:
        await criar_artefato(db, run_id="r1", workspace_id=WS_1)

        padrao = await listar_artefatos(db, [WS_1])
        com_chave = await listar_artefatos(db, [WS_1], incluir_chave=True)

    assert "s3_key" not in padrao["items"][0]
    assert com_chave["items"][0]["s3_key"]


# ── Pagination ───────────────────────────────────────────────────────────────


async def test_a_pagina_tem_teto_proprio_porque_o_MCP_nao_tem_pydantic_na_borda(banco):
    """The route validates `le=200` in the `Query`; MCP has nobody to do it."""
    async with banco() as db:
        for n in range(3):
            await criar_artefato(db, run_id=f"r{n}", workspace_id=WS_1)

        enorme = await listar_artefatos(db, [WS_1], limit=10**9)
        zero = await listar_artefatos(db, [WS_1], limit=0)
        negativo = await listar_artefatos(db, [WS_1], offset=-5)

    assert enorme["limit"] == 200
    assert zero["limit"] == 1
    assert negativo["offset"] == 0


async def test_has_more_diz_a_verdade_nas_duas_bordas(banco):
    async with banco() as db:
        for n in range(3):
            await criar_artefato(db, run_id=f"r{n}", workspace_id=WS_1)

        primeira = await listar_artefatos(db, [WS_1], limit=2)
        ultima = await listar_artefatos(db, [WS_1], limit=2, offset=2)

    assert primeira["has_more"] is True
    assert ultima["has_more"] is False
    assert ultima["total"] == 3


async def test_a_ordenacao_tem_desempate_explicito(banco):
    """Without the `id` tie-breaker, paginating over rows with the same `created_at`
    repeats or loses records — and they are born at the same instant when a run
    writes several output nodes at once.

    This test looks at the SQL, not the result, because of an honest limitation of
    the environment: in SQLite the order without a tie-breaker still comes out
    stable (it falls back to rowid), so behavior does not distinguish the two
    versions. In Postgres, which is the production database, the order of tied
    rows is not guaranteed. What can be asserted here is that the clause is written.
    """
    capturadas: list = []
    async with banco() as db:
        original = db.execute

        async def _espiao(stmt, *a, **kw):
            capturadas.append(stmt)
            return await original(stmt, *a, **kw)

        db.execute = _espiao
        await criar_artefato(db, run_id="r1", workspace_id=WS_1)
        await listar_artefatos(db, [WS_1])

    # The LAST query is the portal layers one; the one that matters is the only
    # one with `ORDER BY`.
    ordenadas = [
        str(c.compile(compile_kwargs={"literal_binds": True})).lower()
        for c in capturadas
        if "order by" in str(c.compile(compile_kwargs={"literal_binds": True})).lower()
    ]
    assert len(ordenadas) == 1, f"esperava uma consulta ordenada, achei {len(ordenadas)}"
    ordem = ordenadas[0].split("order by", 1)[1]
    assert "created_at desc" in ordem
    assert "artifacts.id desc" in ordem, "o desempate sumiu da ordenação"
