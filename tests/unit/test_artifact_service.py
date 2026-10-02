# tests/unit/test_artifact_service.py
"""
A listagem de artefatos como serviço — a porta que os dois transportes usam.

Este arquivo existe por causa de uma medição: com `verify_workspace_access`
apagado do serviço, a suíte inteira continuava verde. O único teste de tenant
que havia cobria o caminho SEM `workspace_id`, onde quem segura é o
`in_(workspace_ids)`; o caminho COM o parâmetro — o único que recebe um valor do
cliente — não tinha nenhum. E é ele que a rota REST expõe direto da query
string.

O que se testa aqui é o serviço, não a tool: a tool tem a própria porta
(`resolver_workspace`) e barraria antes de chegar aqui, mascarando a ausência
desta. A rota não tem nada além disto.
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
    """A regressão medida: sem esta guarda, `GET /artifacts?workspace_id=<alheio>`
    devolvia o acervo do vizinho, e nenhum teste caía."""
    async with banco() as db:
        await criar_artefato(db, run_id="r2", workspace_id=WS_2, filename="alheia.geojson")

        with pytest.raises(HTTPException) as exc:
            await listar_artefatos(db, [WS_1], workspace_id=WS_2)

    assert exc.value.status_code == 403


async def test_o_parametro_estreita_o_escopo_nunca_o_amplia(banco):
    """Pedir um workspace que ESTÁ na lista continua funcionando, e só ele."""
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
    """`in_([])` tem de significar "nada", não "sem filtro"."""
    async with banco() as db:
        await criar_artefato(db, run_id="r1", workspace_id=WS_1)

        pagina = await listar_artefatos(db, [])

    assert pagina["total"] == 0


# ── A busca ──────────────────────────────────────────────────────────────────


async def test_curinga_do_usuario_e_literal_e_nao_varre_tudo(banco):
    """O outro teste de escape olha o SQL, não o TERMO — e é o termo que importa.

    `test_artifacts_busca_por_workflow.py` afirma que a palavra `ESCAPE` aparece
    no SQL renderizado, o que prende o `escape="\\\\"` do `ilike`. O que ele NÃO
    prende é a transformação de `a_b` em `a\\_b`: apagando essa linha, aquele
    teste continua passando e o `_` volta a ser curinga — buscar por `_` passa a
    devolver a coleção inteira, exatamente o que o docstring de lá promete que
    não acontece.

    Aqui a prova é de comportamento, contra o banco: das duas linhas, só a que
    tem o sublinhado LITERAL pode voltar.
    """
    async with banco() as db:
        # `aXb` casa o PADRÃO `a_b` se o `_` for curinga, e não casa se for
        # literal. É a linha que discrimina — sem ela, as duas versões do código
        # devolvem o mesmo e o teste não prova nada.
        await criar_artefato(db, run_id="r1", workspace_id=WS_1, filename="aXb.geojson")
        await criar_artefato(db, run_id="r2", workspace_id=WS_1, filename="a_b.geojson")

        pagina = await listar_artefatos(db, [WS_1], search="a_b")

    assert pagina["total"] == 1, "o sublinhado voltou a ser curinga"
    assert pagina["items"][0]["filename"] == "a_b.geojson"


async def test_porcento_do_usuario_tambem_e_literal(banco):
    async with banco() as db:
        # `100X` casa `100%` com o `%` como curinga; só `100%` casa literal.
        await criar_artefato(db, run_id="r1", workspace_id=WS_1, filename="100X.geojson")
        await criar_artefato(db, run_id="r2", workspace_id=WS_1, filename="100%.geojson")

        pagina = await listar_artefatos(db, [WS_1], search="100%")

    assert pagina["total"] == 1, "o porcento voltou a ser curinga"
    assert pagina["items"][0]["filename"] == "100%.geojson"


# ── A chave do storage não escapa para a REST ────────────────────────────────


async def test_a_chave_do_storage_so_sai_sob_pedido(banco):
    """`incluir_chave` existe para a extração não alargar o contrato da tela.

    O MCP precisa da `s3_key` para decidir se há objeto a assinar; a interface
    não. Sem guarda, um refactor futuro a devolveria para todo mundo e ninguém
    notaria — a resposta só ficaria "um campo maior".
    """
    async with banco() as db:
        await criar_artefato(db, run_id="r1", workspace_id=WS_1)

        padrao = await listar_artefatos(db, [WS_1])
        com_chave = await listar_artefatos(db, [WS_1], incluir_chave=True)

    assert "s3_key" not in padrao["items"][0]
    assert com_chave["items"][0]["s3_key"]


# ── Paginação ────────────────────────────────────────────────────────────────


async def test_a_pagina_tem_teto_proprio_porque_o_MCP_nao_tem_pydantic_na_borda(banco):
    """A rota valida `le=200` no `Query`; o MCP não tem quem o faça."""
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
    """Sem o desempate por `id`, paginar sobre linhas de mesmo `created_at`
    repete ou perde registros — e elas nascem no mesmo instante quando uma
    execução grava vários nós de saída de uma vez.

    Este teste olha o SQL, e não o resultado, por limitação honesta do ambiente:
    no SQLite a ordem sem desempate ainda sai estável (ele cai no rowid), então
    comportamento não distingue as duas versões. Em Postgres, que é o banco de
    produção, a ordem de linhas empatadas não é garantida. O que dá para
    afirmar aqui é que a cláusula está escrita.
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

    # A ÚLTIMA consulta é a das camadas do portal; a que interessa é a única
    # com `ORDER BY`.
    ordenadas = [
        str(c.compile(compile_kwargs={"literal_binds": True})).lower()
        for c in capturadas
        if "order by" in str(c.compile(compile_kwargs={"literal_binds": True})).lower()
    ]
    assert len(ordenadas) == 1, f"esperava uma consulta ordenada, achei {len(ordenadas)}"
    ordem = ordenadas[0].split("order by", 1)[1]
    assert "created_at desc" in ordem
    assert "artifacts.id desc" in ordem, "o desempate sumiu da ordenação"
