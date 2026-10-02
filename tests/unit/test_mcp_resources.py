# tests/unit/test_mcp_resources.py
"""
Os resources `atlans://…` — leitura por URI, com a mesma guarda das tools.

Um resource é atraente justamente porque é barato: o cliente o anexa ao
contexto e o relê sem gastar chamada. É por isso que ele é o lugar onde um
vazamento passaria despercebido — ninguém olha duas vezes para uma URI. Este
arquivo fixa o que importa:

- cada URI registrada responde de fato (template errado não falha no registro,
  falha na leitura);
- o guia entregue por resource é BYTE A BYTE o mesmo da tool: se um dia
  divergirem, um cliente aprende uma coisa e o outro aprende outra;
- `atlans://catalog/nodes` sem `type` nunca devolve o catálogo inteiro num
  blob;
- a execução (`atlans://runs/{id}`) sai com o retrato completo dos nós e com a
  mensagem de erro redigida e em quarentena — é o segundo caminho por onde uma
  string de conexão sairia do servidor;
- escopo insuficiente e workspace fora do alcance do token são recusados —
  aqui também, não só nas tools;
- e a leitura de dados de workspace deixa linha de auditoria, como a tool
  deixaria: sem isso, o resource seria o único caminho do servidor por onde se
  lê um fluxo sem rastro nenhum.

A leitura passa pelo `Client(server)` em processo: é o caminho que exercita o
casamento do template RFC 6570 do SDK, que é onde um `{?type}` mal escrito
apareceria. Sem request HTTP, o escopo chega pelo `ContextVar`.
"""
from __future__ import annotations

import json

import pytest
from mcp import Client

from app.mcp import guia, infra
from app.mcp.escopo import ESCOPO_ATUAL
from app.mcp.servidor import create_mcp_server
from app.mcp.tools.catalogo import get_authoring_guide
from app.models.workflow import Workflow
from tests.unit._mcp_harness import (
    RedisFalso,
    banco_em_memoria,
    criar_run,
    criar_usuario,
    criar_workspace,
    ctx_falso,
    escopo_falso,
    sessao_de,
)

# Uma definition com segredo em claro: se algum resource entregar a definition
# sem redigir, é aqui que aparece.
DEFINITION_COM_SEGREDO = {
    "nodes": [
        {
            "id": "n1",
            "name": "DatabaseSpatialQuery",
            "type": "datasource",
            "properties": {
                "connectionString": "postgresql://usuario:senha-secreta@host/base",  # pragma: allowlist secret
                "query": "SELECT geom FROM lotes",
            },
        },
        {
            "id": "n2",
            "name": "SubWorkflowOutput",
            "type": "output",
            "properties": {"ports": ["camada"]},
        },
    ],
    "edges": [{"source": "n1", "target": "n2", "from_key": "output", "to_key": "camada"}],
}

# Uma execução que falhou com a string de conexão dentro da mensagem — o caso
# que prova que `atlans://runs/{id}` não é uma porta lateral para o segredo que
# a definition já não entrega.
DSN = "postgresql://usuario:SenhaLiteral123@db.interno:5432/geo"  # pragma: allowlist secret

NODE_STATS = {
    "n1": {
        "node_name": "Consulta espacial",
        "status": "failed",
        "duration_ms": 900,
        "error": f"falha ao conectar em {DSN}",
        "output_keys": ["gdf"],
        "output_columns": {"gdf": ["id", "geometry"]},
    },
}


async def _criar_workflow(db, *, id_hash: str, workspace_id: str, name: str, definition: dict):
    wf = Workflow(
        id_hash=id_hash,
        name=name,
        description="fluxo de teste",
        workspace_id=workspace_id,
        definition=definition,
        flag_ative=True,
    )
    db.add(wf)
    await db.commit()
    return wf


@pytest.fixture
async def ambiente(monkeypatch):
    """Dois usuários, dois workspaces, um workflow em cada — e a infra redirecionada.

    O segundo workspace existe para provar o que o primeiro não prova: que um id
    válido de OUTRO workspace não é entregue.
    """
    async with banco_em_memoria() as fabrica:
        async with fabrica() as db:
            await criar_usuario(db, "usr-1", "ana")
            await criar_usuario(db, "usr-2", "bruno")
            await criar_workspace(db, "ws-1", "usr-1", "Principal")
            await criar_workspace(db, "ws-2", "usr-2", "De outra pessoa")
            await _criar_workflow(
                db,
                id_hash="11111111-1111-4111-8111-111111111111",
                workspace_id="ws-1",
                name="Meu fluxo",
                definition=DEFINITION_COM_SEGREDO,
            )
            await _criar_workflow(
                db,
                id_hash="22222222-2222-4222-8222-222222222222",
                workspace_id="ws-2",
                name="Fluxo alheio",
                definition={"nodes": [], "edges": []},
            )
            await criar_run(
                db,
                task_id=RUN_DO_MEU,
                workflow_hash="11111111-1111-4111-8111-111111111111",
                workspace_id="ws-1",
                status="failed",
                error_message=f"psycopg2.OperationalError: {DSN}",
                error_category="transient",
                node_stats=NODE_STATS,
            )
            await criar_run(
                db,
                task_id=RUN_ALHEIO,
                workflow_hash="22222222-2222-4222-8222-222222222222",
                workspace_id="ws-2",
            )
        monkeypatch.setattr(infra, "sessao", sessao_de(fabrica))
        monkeypatch.setattr(infra, "redis_ou_none", lambda: RedisFalso())
        # Nenhum nó desabilitado: a configuração vive numa tabela que o SQLite
        # do harness não cria, e o que este arquivo investiga não é o overlay.
        monkeypatch.setattr(
            "app.services.node_service.disabled_names",
            _sem_desabilitados,
        )
        yield fabrica


async def _sem_desabilitados(_db):
    return set()


ID_DO_MEU = "11111111-1111-4111-8111-111111111111"
ID_DO_ALHEIO = "22222222-2222-4222-8222-222222222222"
RUN_DO_MEU = "run-1111"
RUN_ALHEIO = "run-2222"


async def _ler(uri: str, escopo=None) -> str:
    """Lê uma URI como um cliente leria, com o escopo no `ContextVar`.

    A falha é guardada e relançada DEPOIS de fechar o cliente: deixá-la subir
    por dentro do `async with` a embrulharia num grupo de exceções da sessão, e
    a mensagem do erro — que é o contrato que estes testes conferem —
    desapareceria atrás de "unhandled errors" do grupo de exceções.
    """
    escopo = escopo or escopo_falso(scopes={"workflows:read", "drive:read"})
    token = ESCOPO_ATUAL.set(escopo)
    falha: BaseException | None = None
    resultado = None
    try:
        async with Client(create_mcp_server()) as cliente:
            try:
                resultado = await cliente.read_resource(uri)
            except Exception as exc:  # noqa: BLE001 - relançada abaixo, intacta
                falha = exc
    finally:
        ESCOPO_ATUAL.reset(token)
    if falha is not None:
        raise falha
    return "".join(getattr(c, "text", "") or "" for c in resultado.contents)


# ── Registro ──────────────────────────────────────────────────────────────────


async def test_as_sete_uris_estao_registradas_com_mime_explicito():
    server = create_mcp_server()
    por_uri = {t.uri_template: t for t in await server.list_resource_templates()}
    esperado = {
        "atlans://guide/authoring/{topic}": "text/markdown",
        "atlans://catalog/nodes{?type}": "application/json",
        "atlans://catalog/nodes/{name}": "application/json",
        "atlans://workspaces/{id}/workflows": "application/json",
        "atlans://workflows/{id}": "application/json",
        "atlans://workflows/{id}/contract": "application/json",
        "atlans://runs/{id}": "application/json",
    }
    assert set(esperado) <= set(por_uri)
    for uri, mime in esperado.items():
        assert por_uri[uri].mime_type == mime, f"{uri} sem o mime declarado"


@pytest.mark.parametrize(
    "uri",
    [
        "atlans://guide/authoring/overview",
        "atlans://catalog/nodes",
        "atlans://catalog/nodes?type=spatial",
        "atlans://catalog/nodes/Buffer",
        "atlans://workspaces/ws-1/workflows",
        f"atlans://workflows/{ID_DO_MEU}",
        f"atlans://workflows/{ID_DO_MEU}/contract",
        f"atlans://runs/{RUN_DO_MEU}",
    ],
)
async def test_cada_uri_responde(ambiente, uri):
    conteudo = await _ler(uri)
    assert conteudo.strip(), f"{uri} devolveu vazio"


# ── Guia: o resource é alias da tool ──────────────────────────────────────────


@pytest.mark.parametrize("topico", guia.TOPICOS)
async def test_guia_do_resource_e_identico_ao_da_tool(ambiente, topico):
    escopo = escopo_falso(scopes={"workflows:read"})
    do_resource = await _ler(f"atlans://guide/authoring/{topico}", escopo)
    da_tool = (await get_authoring_guide(ctx_falso(escopo), topic=topico))["markdown"]
    assert do_resource == da_tool == guia.ler_topico(topico)


async def test_topico_desconhecido_nao_e_entregue(ambiente):
    with pytest.raises(Exception) as exc:
        await _ler("atlans://guide/authoring/nao-existe")
    assert "not_found" in str(exc.value)


# ── Catálogo ──────────────────────────────────────────────────────────────────


async def test_catalogo_sem_type_nao_entrega_o_catalogo_inteiro(ambiente):
    """Sem filtro, só o mapa de grupos — o índice inteiro não cabe num blob."""
    corpo = json.loads(await _ler("atlans://catalog/nodes"))
    assert "items" not in corpo
    assert corpo["hint"]
    assert corpo["total"] > 0
    tipos = {t["type"] for t in corpo["types"]}
    assert {"trigger", "spatial", "output"} <= tipos
    assert sum(t["count"] for t in corpo["types"]) == corpo["total"]
    # E o corpo é pequeno de verdade: o índice compacto sozinho passa de 4 KB.
    assert len(await _ler("atlans://catalog/nodes")) < 2000


async def test_catalogo_com_type_traz_so_aquele_grupo(ambiente):
    corpo = json.loads(await _ler("atlans://catalog/nodes?type=trigger"))
    assert corpo["type"] == "trigger"
    assert corpo["items"]
    assert {i["type"] for i in corpo["items"]} == {"trigger"}
    assert corpo["total"] == len(corpo["items"])


async def test_no_do_catalogo_traz_a_ficha_completa(ambiente):
    corpo = json.loads(await _ler("atlans://catalog/nodes/Buffer"))
    assert corpo["name"] == "Buffer"
    assert {p["name"] for p in corpo["properties"]} >= {"distance", "distanceUnit"}


async def test_no_inexistente_e_recusado(ambiente):
    with pytest.raises(Exception) as exc:
        await _ler("atlans://catalog/nodes/NaoExiste")
    assert "not_found" in str(exc.value)


# ── Workflows ─────────────────────────────────────────────────────────────────


async def test_listagem_do_workspace_traz_o_fluxo_com_o_nome_em_quarentena(ambiente):
    corpo = json.loads(await _ler("atlans://workspaces/ws-1/workflows"))
    assert corpo["total"] == 1
    item = corpo["items"][0]
    assert item["id"] == ID_DO_MEU
    assert item["workspace_id"] == "ws-1"
    # Texto escrito por gente nunca sobe ao topo da resposta.
    assert item["untrusted_data"]["name"] == "Meu fluxo"
    assert "name" not in item


async def test_workflow_sai_com_a_definition_redigida(ambiente):
    conteudo = await _ler(f"atlans://workflows/{ID_DO_MEU}")
    corpo = json.loads(conteudo)
    assert corpo["id"] == ID_DO_MEU
    definicao = corpo["untrusted_data"]["definition"]
    propriedades = definicao["nodes"][0]["properties"]
    assert propriedades["connectionString"] == "<REDACTED>"
    assert "senha-secreta" not in conteudo


async def test_contrato_traz_as_portas_declaradas(ambiente):
    corpo = json.loads(await _ler(f"atlans://workflows/{ID_DO_MEU}/contract"))
    # O que a plataforma deduz da definition fica no topo; o NOME de cada porta
    # é escrito por quem edita o fluxo e desce para `untrusted_data`.
    assert corpo["has_output_node"] is True
    assert [p["name"] for p in corpo["untrusted_data"]["outputs"]] == ["camada"]


# ── Execuções ─────────────────────────────────────────────────────────────────


async def test_execucao_traz_o_retrato_completo_dos_nos(ambiente):
    """`full`, e não `summary`: quem anexa uma execução está investigando.

    As saídas de cada nó (`output_keys`/`output_columns`) são o que mostra onde
    a cadeia parou de produzir o que o nó seguinte esperava — e são justamente
    o que o resumo omite.
    """
    corpo = json.loads(await _ler(f"atlans://runs/{RUN_DO_MEU}"))

    assert corpo["run_id"] == RUN_DO_MEU
    assert corpo["workflow_id"] == ID_DO_MEU
    assert corpo["status"] == "failed"
    assert corpo["error_category"] == "transient"
    nos = corpo["untrusted_data"]["node_stats"]
    assert [no["node_id"] for no in nos] == ["n1"]
    assert nos[0]["output_columns"] == {"gdf": ["id", "geometry"]}


async def test_execucao_sai_com_o_erro_redigido_e_fora_do_topo(ambiente):
    """A mensagem de erro é o campo por onde uma senha sai de uma execução."""
    conteudo = await _ler(f"atlans://runs/{RUN_DO_MEU}")
    corpo = json.loads(conteudo)

    assert "error_message" not in corpo
    assert "<REDACTED>" in corpo["untrusted_data"]["error_message"]
    # Nem no erro do run, nem no erro do nó, nem em lugar nenhum do documento.
    assert "SenhaLiteral123" not in conteudo
    assert "<REDACTED>" in corpo["untrusted_data"]["node_stats"][0]["error"]


async def test_execucao_de_outro_workspace_nao_e_entregue(ambiente):
    """Id válido de uma execução que existe — e a resposta é a do id inexistente."""
    with pytest.raises(Exception) as alheia:
        await _ler(f"atlans://runs/{RUN_ALHEIO}")
    with pytest.raises(Exception) as inexistente:
        await _ler("atlans://runs/run-que-nunca-existiu")

    assert "not_found" in str(alheia.value)
    assert str(alheia.value) == str(inexistente.value)


# ── Guardas ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "uri",
    [
        "atlans://guide/authoring/overview",
        "atlans://catalog/nodes",
        "atlans://catalog/nodes/Buffer",
        "atlans://workspaces/ws-1/workflows",
        f"atlans://workflows/{ID_DO_MEU}",
        f"atlans://workflows/{ID_DO_MEU}/contract",
        f"atlans://runs/{RUN_DO_MEU}",
    ],
)
async def test_escopo_insuficiente_e_recusado(ambiente, uri):
    """Um token só de Drive não lê nada de workflow — nem por resource."""
    sem_leitura = escopo_falso(scopes={"drive:read"})
    with pytest.raises(Exception) as exc:
        await _ler(uri, sem_leitura)
    mensagem = str(exc.value)
    assert "forbidden_scope" in mensagem
    assert "workflows:read" in mensagem


async def test_workflow_de_outro_workspace_nao_e_entregue(ambiente):
    """Id válido, fluxo existente — e mesmo assim nada sai, nem o nome."""
    for uri in (f"atlans://workflows/{ID_DO_ALHEIO}", f"atlans://workflows/{ID_DO_ALHEIO}/contract"):
        with pytest.raises(Exception) as exc:
            await _ler(uri)
        mensagem = str(exc.value)
        assert "Fluxo alheio" not in mensagem
        assert "forbidden" in mensagem or "not_found" in mensagem


async def test_workspace_fora_do_alcance_do_token_nao_lista(ambiente):
    with pytest.raises(Exception) as exc:
        await _ler("atlans://workspaces/ws-2/workflows")
    mensagem = str(exc.value)
    assert "Fluxo alheio" not in mensagem
    assert "forbidden" in mensagem or "not_found" in mensagem


async def test_leitura_sem_identidade_nenhuma_e_recusada(ambiente):
    """Sem PAT resolvido não há escopo, e um resource não é caminho alternativo."""
    token = ESCOPO_ATUAL.set(None)
    try:
        async with Client(create_mcp_server()) as cliente:
            with pytest.raises(Exception) as exc:
                await cliente.read_resource("atlans://catalog/nodes")
    finally:
        ESCOPO_ATUAL.reset(token)
    assert "forbidden" in str(exc.value)


# ── Auditoria ─────────────────────────────────────────────────────────────────


def _linhas_de_auditoria(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == "app.mcp.auditoria"]


@pytest.mark.parametrize(
    "uri,guarda",
    [
        ("atlans://workspaces/ws-1/workflows", "list_workflows"),
        (f"atlans://workflows/{ID_DO_MEU}", "get_workflow"),
        (f"atlans://workflows/{ID_DO_MEU}/contract", "get_workflow_contract"),
        (f"atlans://runs/{RUN_DO_MEU}", "get_run"),
    ],
)
async def test_leitura_de_dados_de_workspace_deixa_linha_de_auditoria(ambiente, caplog, uri, guarda):
    """O resource é barato de repetir — e por isso não pode ser o caminho sem rastro."""
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        await _ler(uri)
    linhas = _linhas_de_auditoria(caplog)
    assert len(linhas) == 1
    assert f"resource={guarda}" in linhas[0]
    assert "desfecho=ok" in linhas[0]
    # O id do fluxo é argumento do cliente: não entra na linha.
    assert ID_DO_MEU not in linhas[0]


async def test_recusa_de_resource_tambem_e_auditada(ambiente, caplog):
    sem_leitura = escopo_falso(scopes={"drive:read"})
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        with pytest.raises(Exception):
            await _ler(f"atlans://workflows/{ID_DO_MEU}", sem_leitura)
    linhas = _linhas_de_auditoria(caplog)
    assert linhas and "desfecho=recusa:forbidden_scope" in linhas[0]


async def test_catalogo_e_guia_nao_gastam_linha_de_auditoria(ambiente, caplog):
    """Texto fixo da instalação, igual para todo token: não há dado de ninguém."""
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        await _ler("atlans://catalog/nodes")
        await _ler("atlans://guide/authoring/overview")
    assert _linhas_de_auditoria(caplog) == []


async def test_resource_nao_consome_o_balde_de_cota(ambiente, monkeypatch):
    """A isenção é decisão documentada: o resource é alias de uma tool que já conta."""
    redis = RedisFalso()
    monkeypatch.setattr(infra, "redis_ou_none", lambda: redis)
    await _ler(f"atlans://workflows/{ID_DO_MEU}")
    assert not [c for c in redis.chamadas if c[0] == "incr"]
