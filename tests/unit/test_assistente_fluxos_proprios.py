# tests/unit/test_agente_fluxos_proprios.py
"""
`list_workflows` e os fluxos que o PROPRIO assistente criou.

A listagem esconde `origem = "assistente"` por padrao — os fluxos do assistente
sao meio de entrega da Home, nao itens que o dono gerencia. O efeito colateral
era cruel e silencioso: quem chama a tool NA HOME e o proprio assistente, e o
default `False` o cegava para o que ele mesmo tinha criado. Num chat novo, «roda
de novo aquele do desmatamento» nao encontrava nada e nascia um fluxo duplicado
a cada pergunta recorrente.

O corte e pelo ESCOPO (`origem_dos_fluxos == "assistente"`), nao por um
parametro que o modelo precise lembrar de passar: um PAT comum continua com o
default `False`, e o campo `origem` de cada item diz o que e de quem.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.mcp import infra
from app.mcp.tools.workflows import list_workflows
from app.models.base import Base
from app.models.workflow import Workflow
from tests.unit._mcp_harness import TABELAS, criar_usuario, criar_workspace, ctx_falso, escopo_falso

pytestmark = pytest.mark.asyncio

WS = "11111111-1111-4111-8111-111111111111"
DELA = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DELE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


@pytest.fixture
async def banco(monkeypatch):
    """Um workspace com DOIS fluxos: um da pessoa, um do assistente."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def _sessao():
        async with fabrica() as db:
            try:
                yield db
            finally:
                await db.rollback()

    monkeypatch.setattr(infra, "sessao", _sessao)

    async with fabrica() as db:
        await criar_usuario(db, "usr-1", "ana")
        await criar_workspace(db, WS, "usr-1", "Principal")
        db.add(Workflow(
            id_hash=DELA, name="Recorte mensal", workspace_id=WS,
            definition={"nodes": [], "edges": []}, flag_ative=True, origem="usuario",
        ))
        db.add(Workflow(
            id_hash=DELE, name="assistente: desmatamento 2024", workspace_id=WS,
            definition={"nodes": [], "edges": []}, flag_ative=True, origem="assistente",
        ))
        await db.commit()

    yield fabrica
    await engine.dispose()


def _ctx(**kw):
    campos = {"scopes": {"workflows:read"}, "workspace_ids": {WS}}
    campos.update(kw)
    return ctx_falso(escopo_falso(**campos))


async def test_o_assistente_enxerga_os_proprios_fluxos(banco):
    saida = await list_workflows(_ctx(origem_dos_fluxos="assistente"))

    ids = {i["id"] for i in saida["items"]}
    assert ids == {DELA, DELE}
    origens = {i["id"]: i["origem"] for i in saida["items"]}
    assert origens[DELE] == "assistente"
    assert origens[DELA] == "usuario"


async def test_pat_comum_continua_sem_ver_os_do_assistente(banco):
    saida = await list_workflows(_ctx())

    assert {i["id"] for i in saida["items"]} == {DELA}
    assert saida["total"] == 1


async def test_pat_pode_pedir_os_do_assistente_explicitamente(banco):
    """O equivalente ao `?assistente=1` da REST, para quem quiser o acervo todo."""
    saida = await list_workflows(_ctx(), incluir_do_assistente=True)

    assert {i["id"] for i in saida["items"]} == {DELA, DELE}


async def test_o_assistente_pode_abrir_mao_de_ver_os_proprios(banco):
    """O parametro explicito vence o default derivado do escopo."""
    saida = await list_workflows(
        _ctx(origem_dos_fluxos="assistente"), incluir_do_assistente=False
    )

    assert {i["id"] for i in saida["items"]} == {DELA}
