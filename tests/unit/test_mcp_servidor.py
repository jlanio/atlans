# tests/unit/test_mcp_servidor.py
"""
O servidor `/mcp` inteiro: fábrica, filtro de catálogo, guarda de escopo e borda.

Este arquivo exercita a pilha real — middleware de PAT + transporte streamable
HTTP + `ServidorAtlans` — porque é a composição que erra: um filtro que funciona
no objeto e não funciona por HTTP não protege ninguém.

Os pontos fixados aqui:

- `create_mcp_server()` é fábrica. `session_manager.run()` só pode ser entrado
  UMA vez por instância; um singleton de módulo faria o segundo teste (ou um
  reload em produção) encontrar o gerenciador já consumido;
- o `initialize` responde nos dois caminhos que os clientes usam: o legado, que
  fixa `protocolVersion` e fala JSON-RPC cru, e o moderno do SDK;
- `tools/list` esconde o que o token não alcança — nos dois caminhos, porque o
  escopo chega ao `list_tools` por um `ContextVar` e é preciso provar que ele
  sobrevive à task que o transporte cria;
- esconder é conforto; a garantia é `call_tool`, que recusa nomeando o escopo
  que falta mesmo quando o cliente chama um nome que nunca viu na lista;
- o default é RECUSAR: tool sem linha em `GUARDAS` não aparece no catálogo e não
  roda. É o caso que falharia ABERTO se o default fosse delegar ao SDK — uma
  tool nova rodaria sem escopo, sem cota e sem papel;
- toda chamada deixa UMA linha de auditoria, inclusive a que foi recusada pela
  guarda, e nenhuma delas carrega os argumentos;
- `Host` fora da lista é 421 e `Origin` presente é 403 — mas sem PAT o 401 vem
  ANTES, porque o middleware é externo ao transporte.

Como as tools de domínio ainda não existem, os testes registram tools próprias
na instância do teste, com os nomes que a tabela de guardas conhece.
"""
from __future__ import annotations

import json

import httpx
import pytest
from mcp.server.mcpserver import Context

from app.mcp import cotas, infra
from app.mcp.escopo import ESCOPO_ATUAL
from app.mcp.guardas import GUARDAS
from app.mcp.instrucoes import INSTRUCOES
from app.mcp.servidor import (
    VERSAO_MCP,
    ServidorAtlans,
    create_mcp_server,
    criar_app_mcp,
    hosts_permitidos,
)
from tests.unit._mcp_harness import (
    RedisFalso,
    banco_em_memoria,
    cliente_mcp,
    criar_pat,
    criar_usuario,
    criar_workspace,
    ctx_falso,
    escopo_falso,
    sessao_de,
)

_JSON = {
    "Content-Type": "application/json",
    # Sem os dois tipos no Accept o transporte responde 406 antes de olhar o resto.
    "Accept": "application/json, text/event-stream",
}

_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "cliente-de-teste", "version": "0"},
    },
}


def servidor_de_teste():
    """Servidor sem as tools reais, com duas de mentira — uma por escopo da tabela.

    O que se exercita aqui é a COMPOSIÇÃO (filtro de catálogo, guarda de escopo,
    cota, auditoria), não o corpo de nenhuma tool. Por isso a instância é montada
    à mão em vez de sair de `create_mcp_server()`: com as tools reais registradas,
    um segundo registro com o mesmo nome seria ignorado pelo SDK e os testes
    estariam medindo a tool de produção sem querer. Os nomes continuam sendo dois
    da tabela de guardas, que é o que dá sentido ao filtro por escopo.
    """
    server = ServidorAtlans(
        name="atlans",
        title="Atlans",
        instructions=INSTRUCOES,
        version=VERSAO_MCP,
    )

    @server.tool(name="list_workspaces", description="Lista workspaces (tool de teste).")
    async def _workspaces() -> dict:
        return {"items": []}

    @server.tool(name="list_drive_files", description="Lista arquivos do Drive (tool de teste).")
    async def _drive() -> dict:
        return {"items": []}

    return server


def _resposta_jsonrpc(r: httpx.Response) -> dict:
    """O corpo JSON-RPC, venha ele como JSON ou dentro de um evento SSE."""
    if r.headers.get("content-type", "").startswith("application/json"):
        return r.json()
    for linha in r.text.splitlines():
        if linha.startswith("data: "):
            return json.loads(linha[len("data: ") :])
    raise AssertionError(f"sem payload JSON-RPC em: {r.text!r}")


@pytest.fixture
async def ambiente(monkeypatch):
    """Banco em memória com um usuário e um workspace; infra do MCP redirecionada."""
    async with banco_em_memoria() as fabrica:
        async with fabrica() as db:
            await criar_usuario(db, "usr-1", "ana")
            await criar_workspace(db, "ws-1", "usr-1", "Principal")
        redis = RedisFalso()
        monkeypatch.setattr(infra, "sessao", sessao_de(fabrica))
        monkeypatch.setattr(infra, "redis_ou_none", lambda: redis)
        yield fabrica


async def _pat(fabrica, escopos) -> str:
    async with fabrica() as db:
        return await criar_pat(db, "usr-1", escopos, None)


# ── Fábrica ───────────────────────────────────────────────────────────────────


def test_a_fabrica_devolve_instancias_independentes():
    a, b = create_mcp_server(), create_mcp_server()
    assert a is not b
    # Cada instância tem o seu gerenciador de sessões — é o que permite um
    # servidor por teste sem "cannot be used twice".
    criar_app_mcp(a)
    criar_app_mcp(b)
    assert a.session_manager is not b.session_manager


def test_criar_app_mcp_duas_vezes_devolve_o_mesmo_app():
    """Duas chamadas trocariam o `session_manager` em silêncio.

    `streamable_http_app()` cria um gerenciador novo a cada chamada, e quem
    entra no gerenciador é o `lifespan` de `app.main`, uma vez só: um segundo
    app deixaria o servido com um gerenciador que ninguém iniciou.
    """
    server = create_mcp_server()
    primeiro = criar_app_mcp(server)
    gerenciador = server.session_manager
    assert criar_app_mcp(server) is primeiro
    assert server.session_manager is gerenciador


def test_a_fabrica_carrega_identidade_e_instrucoes():
    """A versão fica presa de propósito: mudá-la tem de ser deliberado.

    É o único discriminador que um cliente tem para saber QUAL contrato está no
    ar — foi o que faltou na conferência da entrega anterior, quando o `1.0.0`
    parado impediu de distinguir, pelo `initialize`, o servidor novo do antigo.
    Ferramenta nova sobe a menor; ferramenta removida fica uma versão menor
    marcada como obsoleta antes de sumir.
    """
    server = create_mcp_server()
    assert server.name == "atlans"
    assert server.instructions == INSTRUCOES
    assert VERSAO_MCP == "1.5.0"


def test_hosts_permitidos_vem_da_configuracao(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config, "MCP_ALLOWED_HOSTS", ["atlans.example.org", "localhost:*"])
    assert hosts_permitidos() == ["atlans.example.org", "localhost:*"]


def test_default_dos_hosts_cobre_o_site_e_o_desenvolvimento():
    """Sem MCP_ALLOWED_HOSTS, valem o host do FRONTEND_URL e o dev local."""
    from app.core import config

    assert config.hosts_mcp_padrao("https://atlans.example.org")[:2] == [
        "atlans.example.org", "atlans.example.org:*",
    ]
    assert "localhost:*" in config.MCP_ALLOWED_HOSTS


# ── Paridade tools × guardas ──────────────────────────────────────────────────


async def test_toda_tool_registrada_tem_guarda():
    """Nenhuma tool registrada fica sem linha na tabela de guardas.

    Segunda linha de defesa, e de propósito: em produção a tool sem guarda já é
    escondida e recusada, mas isso a torna INÚTIL em silêncio. Este teste é o
    que avisa em CI — e por isso ele lê o catálogo CRU do SDK
    (`MCPServer.list_tools`), sem o filtro do `ServidorAtlans`, senão a tool
    esquecida sumiria da lista e o teste passaria sem ver nada.
    """
    from mcp.server.mcpserver import MCPServer

    server = create_mcp_server()
    nomes = {t.name for t in await MCPServer.list_tools(server)}
    assert nomes, "o catálogo não pode estar vazio"
    assert nomes <= set(GUARDAS)


async def test_o_catalogo_cru_e_o_filtrado_coincidem_no_servidor_real():
    """Com a tabela em dia, esconder não tira nada de quem tem escopo total."""
    from mcp.server.mcpserver import MCPServer

    server = create_mcp_server()
    crus = {t.name for t in await MCPServer.list_tools(server)}
    # Escopo total = a união do que a tabela exige; assim a lista não envelhece
    # quando uma tool nova traz um escopo que ninguém usava.
    ficha = ESCOPO_ATUAL.set(
        escopo_falso(scopes={g.escopo for g in GUARDAS.values()})
    )
    try:
        filtrados = {t.name for t in await server.list_tools()}
    finally:
        ESCOPO_ATUAL.reset(ficha)
    assert filtrados == crus


# As tools de leitura, separadas das demais porque é sobre elas que valem as
# promessas de "não muda nada e não gasta balde extra".
TOOLS_DE_LEITURA = {
    "list_workspaces",
    "list_workflows",
    "get_workflow",
    "get_workflow_contract",
    "search_nodes",
    "describe_node",
    "list_credentials",
    "list_drive_files",
    "get_drive_download_url",
    "get_portal_info",
    "get_authoring_guide",
    "get_run",
    "list_runs",
    "get_run_artifacts",
    # Fase 2: ler o log de uma execução é leitura como o resto da
    # observabilidade — não interrompe nem dispara nada.
    "get_run_events",
    # Fase 2, acervo: o histórico e o que as execuções produziram. Ler uma
    # versão antiga não muda nada; `list_artifacts` assina URL, o que a torna
    # não idempotente, mas continua sendo leitura.
    "list_workflow_versions",
    "get_workflow_version",
    "list_artifacts",
    # Fase 2, pins: saber QUAIS saídas estão congeladas é leitura — e é a
    # única forma de descobrir que um resultado veio de cache.
    "list_pins",
    # Fase 2, gatilhos: ver QUANDO um fluxo dispara sozinho é leitura, e pede
    # `workflows:read` e não `triggers:manage` — pelo mesmo motivo de
    # `get_run`: quem só acompanha não precisa de poder para mexer.
    "list_schedules",
    # Fontes: buscar e descrever são leitura da tabela, sem rede.
    "search_sources",
    "describe_source",
}


def test_a_tabela_de_guardas_tem_exatamente_as_tools_registradas():
    """A lista é escrita à mão de propósito.

    Derivá-la de `GUARDAS` tornaria o teste tautológico: ele passaria a afirmar
    que a tabela é igual a si mesma, e uma tool nova entraria sem ninguém
    decidir se ela lê ou escreve. Manter as duas listas e compará-las é o que
    obriga essa decisão a ser tomada por uma pessoa.
    """
    assert set(GUARDAS) == TOOLS_DE_LEITURA | {
        "validate_workflow",
        "create_workflow",
        "update_workflow",
        "set_workflow_active",
        "set_portal_access",
        "run_workflow",
        # Fase 2 — mexem no que está rodando.
        "cancel_run",
        "retry_run",
        # Fase 2 — acervo: as duas que escrevem.
        "restore_workflow_version",
        "duplicate_workflow",
        # Fase 2 — pins: as duas mudam a coluna do workflow.
        "pin_node_output",
        "unpin_node_output",
        # Fase 2 — gatilhos: as três mexem em quando o fluxo dispara sozinho.
        "create_schedule",
        "update_schedule",
        "delete_schedule",
        # Fase 2 — escrita no Drive: as três mexem no acervo do workspace.
        "create_drive_upload_url",
        "confirm_drive_upload",
        "delete_drive_file",
        # Fontes: `probe_source` fala com a internet, atualiza o estado de uma
        # fonte já catalogada e paga balde — não é leitura, como
        # `validate_workflow` não é; `register_source` sonda E grava.
        "probe_source",
        "register_source",
    }


def test_toda_guarda_de_leitura_e_somente_leitura_e_nao_gasta_cota():
    for nome in TOOLS_DE_LEITURA:
        guarda = GUARDAS[nome]
        assert guarda.read_only is True, nome
        assert guarda.cota is None, nome
    # A URL pré-assinada é a única que muda a cada chamada (assinatura nova) —
    # tanto a do Drive quanto as dos artefatos de um run.
    assert GUARDAS["get_drive_download_url"].idempotente is False
    assert GUARDAS["get_run_artifacts"].idempotente is False


def test_ler_execucao_nao_exige_escopo_de_disparo():
    """Acompanhar um run é leitura; disparar é outra coisa.

    Paridade com a REST, onde `/observability` só pede ser membro do
    workspace. Se `get_run` passasse a exigir `runs:execute`, quem quisesse
    apenas acompanhar precisaria de um token capaz de DISPARAR — um escopo
    maior do que a tarefa, que é o oposto do que esta tabela existe para
    garantir.
    """
    for nome in ("get_run", "list_runs", "get_run_artifacts"):
        assert GUARDAS[nome].escopo == "workflows:read", nome
        assert GUARDAS[nome].papel == "viewer", nome
    assert GUARDAS["run_workflow"].escopo == "runs:execute"
    assert GUARDAS["run_workflow"].papel == "operator"


def test_toda_guarda_de_escrita_nao_e_somente_leitura():
    """Escrever nunca pode anunciar `readOnlyHint` — o cliente confia nisso.

    A anotação é o que faz um cliente decidir se pede confirmação antes de
    chamar. Uma tool que grava anunciando-se como leitura roda sem ninguém
    perguntar nada.
    """
    for nome, guarda in GUARDAS.items():
        if nome in TOOLS_DE_LEITURA:
            continue
        assert guarda.read_only is False, nome
        assert guarda.escopo in (
            "workflows:write", "runs:execute", "triggers:manage", "drive:write",
        ), nome
        assert guarda.papel in ("editor", "operator"), nome


# Os dois baldes extras, escritos à mão pelo mesmo motivo da lista de leitura:
# derivá-los da tabela faria o teste concordar com qualquer valor que lá
# estivesse. `run` é de quem reserva um executor; `validate` é de quem roda a
# simulação da definição — que `create` e `update` fazem antes de gravar.
TOOLS_QUE_DESPACHAM = {"run_workflow", "retry_run"}
TOOLS_QUE_SIMULAM = {"validate_workflow", "create_workflow", "update_workflow"}
# As que SONDAM um WFS de terceiro (GetCapabilities/DescribeFeatureType): I/O
# contra fora, com balde próprio, mais apertado que o de validação.
TOOLS_QUE_SONDAM = {"probe_source", "register_source"}


def test_cada_balde_de_cota_cobre_exatamente_quem_gasta_o_recurso():
    """Sem isto, `retry_run` podia perder a cota e continuar passando.

    A cota `run` é o que impede um agente em laço de encher a fila de execuções
    — e `retry_run` dispara uma execução por chamada, como `run_workflow`. Os
    outros testes de guarda conferem `read_only`, `escopo` e `papel`, e nenhum
    olhava para `cota`: apagar `"run"` da linha de `retry_run` passava inteiro.
    """
    for nome, guarda in GUARDAS.items():
        if nome in TOOLS_QUE_DESPACHAM:
            esperado = "run"
        elif nome in TOOLS_QUE_SIMULAM:
            esperado = "validate"
        elif nome in TOOLS_QUE_SONDAM:
            esperado = "probe"
        else:
            esperado = None
        assert guarda.cota == esperado, f"{nome}: cota {guarda.cota!r}, esperado {esperado!r}"


def test_o_hint_de_idempotencia_de_cada_tool_e_uma_decisao_registrada():
    """`idempotentHint` é publicado ao cliente, e ele age em cima.

    Uma tool anunciada como idempotente autoriza o agente a repetir a chamada
    depois de um erro de rede. Em `retry_run` cada repetição é uma execução
    NOVA, com executor reservado — por isso ela é a única das três de execução
    marcada como não idempotente, e por isso o valor precisa estar preso aqui:
    nenhum outro teste de guarda olhava para este campo.
    """
    nao_idempotentes = {
        # Assinam URL nova a cada chamada.
        "get_drive_download_url", "get_run_artifacts",
        "list_artifacts",
        # Gravam ou disparam algo diferente a cada chamada.
        "create_workflow", "update_workflow", "run_workflow", "retry_run",
        # Restaurar grava um auto-snapshot novo a cada chamada; duplicar cria
        # um fluxo novo com id novo.
        "restore_workflow_version", "duplicate_workflow",
        # Cada chamada cria um `job_id` novo: repetir depois de um erro de rede
        # deixaria DOIS agendamentos disparando o mesmo fluxo.
        "create_schedule",
        # Cada chamada cria uma linha pendente e assina uma URL nova.
        "create_drive_upload_url",
    }
    # Os pins NÃO entram: `pin_node_output` reescreve a mesma entrada e
    # `unpin_node_output` removê-la duas vezes não muda nada. São as únicas
    # tools de escrita do servidor que podem ser repetidas com segurança, e
    # deixar isso explícito aqui é o que impede alguém de "corrigir" a linha
    # delas em `GUARDAS` por analogia com as outras escritas.
    assert not ({"pin_node_output", "unpin_node_output"} & nao_idempotentes)
    for nome, guarda in GUARDAS.items():
        esperado = nome not in nao_idempotentes
        assert guarda.idempotente is esperado, (
            f"{nome}: idempotente={guarda.idempotente}, esperado {esperado}"
        )


# ── list_tools filtrado ───────────────────────────────────────────────────────


async def test_sem_escopo_no_contexto_a_lista_sai_inteira():
    """É o caso do cliente em processo, que não passa pelo middleware."""
    server = servidor_de_teste()
    assert ESCOPO_ATUAL.get() is None
    assert {t.name for t in await server.list_tools()} == {"list_workspaces", "list_drive_files"}


async def test_lista_filtrada_no_caminho_moderno(ambiente):
    segredo = await _pat(ambiente, ["workflows:read"])
    server = servidor_de_teste()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with cliente_mcp(app_mcp, segredo) as cliente:
            nomes = {t.name for t in (await cliente.list_tools()).tools}
    assert nomes == {"list_workspaces"}


async def test_lista_filtrada_no_caminho_legado(ambiente):
    segredo = await _pat(ambiente, ["drive:read"])
    server = servidor_de_teste()
    app_mcp = criar_app_mcp(server)
    cabecalhos = {**_JSON, "Authorization": f"Bearer {segredo}"}
    async with server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_mcp), base_url="http://localhost:8000"
        ) as c:
            r = await c.post("/mcp", json=_INITIALIZE, headers=cabecalhos)
            assert r.status_code == 200, r.text
            corpo = _resposta_jsonrpc(r)
            assert corpo["result"]["serverInfo"]["name"] == "atlans"

            r = await c.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                headers=cabecalhos,
            )
            assert r.status_code == 200, r.text
            nomes = {t["name"] for t in _resposta_jsonrpc(r)["result"]["tools"]}
    assert nomes == {"list_drive_files"}


async def test_token_com_os_dois_escopos_ve_as_duas_tools(ambiente):
    segredo = await _pat(ambiente, ["workflows:read", "drive:read"])
    server = servidor_de_teste()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with cliente_mcp(app_mcp, segredo) as cliente:
            nomes = {t.name for t in (await cliente.list_tools()).tools}
    assert nomes == {"list_workspaces", "list_drive_files"}


# ── call_tool ─────────────────────────────────────────────────────────────────


async def test_tool_com_o_escopo_certo_roda(ambiente):
    segredo = await _pat(ambiente, ["workflows:read"])
    server = servidor_de_teste()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with cliente_mcp(app_mcp, segredo) as cliente:
            resultado = await cliente.call_tool("list_workspaces", {})
    assert resultado.is_error is False


async def test_chamar_tool_escondida_e_recusado_nomeando_o_escopo_que_falta(ambiente):
    """Filtrar a lista é conforto; a garantia é esta recusa."""
    segredo = await _pat(ambiente, ["drive:read"])
    server = servidor_de_teste()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with cliente_mcp(app_mcp, segredo) as cliente:
            resultado = await cliente.call_tool("list_workspaces", {})
    assert resultado.is_error is True
    corpo = json.loads(resultado.content[0].text)
    assert corpo["code"] == "forbidden_scope"
    assert corpo["missing_scope"] == "workflows:read"


async def test_chamada_sem_identidade_nenhuma_e_proibida():
    """Cliente em processo: sem middleware, sem escopo — a tool não roda."""
    server = servidor_de_teste()
    from mcp import Client

    async with Client(server) as cliente:
        resultado = await cliente.call_tool("list_workspaces", {})
    assert resultado.is_error is True
    assert json.loads(resultado.content[0].text)["code"] == "forbidden"


async def test_cota_estourada_recusa_a_chamada_antes_de_rodar_a_tool(ambiente, monkeypatch):
    segredo = await _pat(ambiente, ["workflows:read"])
    redis = RedisFalso()
    monkeypatch.setattr(infra, "redis_ou_none", lambda: redis)
    # O balde geral deste token já chega no teto.
    redis.dados[f"ratelimit:mcp:{await _token_id(ambiente)}:geral"] = cotas.LIMITE_GERAL

    server = servidor_de_teste()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with cliente_mcp(app_mcp, segredo) as cliente:
            resultado = await cliente.call_tool("list_workspaces", {})
    assert resultado.is_error is True
    assert json.loads(resultado.content[0].text)["code"] == "rate_limited"


async def _token_id(fabrica) -> str:
    from sqlalchemy import select

    from app.models.api_token import ApiToken

    async with fabrica() as db:
        return (await db.execute(select(ApiToken.id_hash))).scalars().first()


# ── Tool sem guarda: o default é recusar ──────────────────────────────────────


def _servidor_com_tool_sem_guarda(nome: str = "tool_sem_guarda"):
    """Servidor com uma única tool que NÃO tem linha na tabela de guardas.

    É o esquecimento que se quer cobrir: alguém registra a tool e não declara a
    guarda. Antes, o servidor delegava ao SDK e a tool rodava sem escopo, sem
    cota e sem papel — exatamente o contrário do que a tabela existe para fazer.
    """
    server = ServidorAtlans(
        name="atlans", title="Atlans", instructions=INSTRUCOES, version=VERSAO_MCP,
    )
    rastro = {"rodou": False}

    @server.tool(name=nome, description="Tool sem linha em GUARDAS (teste).")
    async def _sem_guarda() -> dict:
        rastro["rodou"] = True
        return {"segredo_da_casa": "nunca deveria sair"}

    return server, rastro


async def test_tool_sem_guarda_nao_aparece_no_catalogo():
    server, _ = _servidor_com_tool_sem_guarda()
    assert await server.list_tools() == []


async def test_tool_sem_guarda_e_recusada_sem_rodar_o_corpo():
    """O default invertido: sem guarda declarada, a chamada não acontece."""
    from mcp import Client

    server, rastro = _servidor_com_tool_sem_guarda()
    ficha = ESCOPO_ATUAL.set(escopo_falso(scopes={"workflows:read", "drive:read"}))
    try:
        async with Client(server) as cliente:
            resultado = await cliente.call_tool("tool_sem_guarda", {})
    finally:
        ESCOPO_ATUAL.reset(ficha)

    assert resultado.is_error is True
    assert rastro["rodou"] is False
    corpo = json.loads(resultado.content[0].text)
    assert corpo["code"] == "not_found"
    # A recusa não conta ao cliente se o nome existe e ficou sem guarda ou se
    # nunca existiu — e não carrega nada de dentro da tool.
    assert "GUARDAS" not in json.dumps(corpo)
    assert "segredo_da_casa" not in json.dumps(corpo)


async def test_nome_que_nunca_existiu_recebe_a_mesma_recusa():
    from mcp import Client

    server = servidor_de_teste()
    ficha = ESCOPO_ATUAL.set(escopo_falso(scopes={"workflows:read"}))
    try:
        async with Client(server) as cliente:
            resultado = await cliente.call_tool("delete_tudo", {})
    finally:
        ESCOPO_ATUAL.reset(ficha)
    assert resultado.is_error is True
    assert json.loads(resultado.content[0].text)["code"] == "not_found"


# ── Auditoria ─────────────────────────────────────────────────────────────────


def _linhas_de_auditoria(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == "app.mcp.auditoria"]


async def _chamar_em_processo(server, nome: str, argumentos: dict, escopo):
    """Chama uma tool pelo cliente em processo, com o escopo no `ContextVar`."""
    from mcp import Client

    ficha = ESCOPO_ATUAL.set(escopo)
    try:
        async with Client(server) as cliente:
            return await cliente.call_tool(nome, argumentos)
    finally:
        ESCOPO_ATUAL.reset(ficha)


async def test_chamada_bem_sucedida_deixa_uma_linha_de_auditoria(caplog):
    server = servidor_de_teste()
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        resultado = await _chamar_em_processo(
            server, "list_workspaces", {}, escopo_falso(scopes={"workflows:read"})
        )
    assert resultado.is_error is False
    linhas = _linhas_de_auditoria(caplog)
    assert len(linhas) == 1
    assert "tool=list_workspaces" in linhas[0]
    assert "desfecho=ok" in linhas[0]
    # O prefixo identifica o token; o segredo nunca aparece.
    assert "token=atl_pat_Ab3d" in linhas[0]


async def test_recusa_por_falta_de_escopo_tambem_e_auditada(caplog):
    """A chamada barrada é justamente a que mais interessa registrar."""
    server = servidor_de_teste()
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        resultado = await _chamar_em_processo(
            server, "list_workspaces", {}, escopo_falso(scopes={"drive:read"})
        )
    assert resultado.is_error is True
    linhas = _linhas_de_auditoria(caplog)
    assert len(linhas) == 1
    assert "desfecho=recusa:forbidden_scope" in linhas[0]


async def test_recusa_por_cota_tambem_e_auditada(caplog, monkeypatch):
    server = servidor_de_teste()
    redis = RedisFalso()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.LIMITE_GERAL
    monkeypatch.setattr(infra, "redis_ou_none", lambda: redis)
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        resultado = await _chamar_em_processo(
            server, "list_workspaces", {}, escopo_falso(scopes={"workflows:read"})
        )
    assert resultado.is_error is True
    assert "desfecho=recusa:rate_limited" in _linhas_de_auditoria(caplog)[0]


async def test_a_auditoria_nunca_registra_os_argumentos_da_chamada(caplog):
    """Sem este teste, um mutante que acrescentasse `arguments=%s` passaria.

    O argumento é dado do usuário: nome de arquivo, texto de busca, id de
    workflow. A linha de auditoria diz QUEM chamou O QUÊ e como terminou —
    nunca com quê.
    """
    sentinela = "SENTINELA-9f3c-nome-do-no"
    server = ServidorAtlans(
        name="atlans", title="Atlans", instructions=INSTRUCOES, version=VERSAO_MCP,
    )

    @server.tool(name="describe_node", description="Devolve o nome recebido (teste).")
    async def _descrever(name: str) -> dict:
        return {"name": name}

    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        resultado = await _chamar_em_processo(
            server, "describe_node", {"name": sentinela}, escopo_falso(scopes={"workflows:read"})
        )

    assert resultado.is_error is False
    linhas = _linhas_de_auditoria(caplog)
    assert len(linhas) == 1
    assert "tool=describe_node" in linhas[0]
    assert sentinela not in linhas[0]


async def test_tool_que_falha_registra_o_codigo_do_erro(caplog):
    """Falha da tool e recusa de guarda têm desfechos diferentes de propósito."""
    from mcp.server.mcpserver.exceptions import ToolError

    from app.mcp.erros import erro as montar_erro

    server = ServidorAtlans(
        name="atlans", title="Atlans", instructions=INSTRUCOES, version=VERSAO_MCP,
    )

    @server.tool(name="get_workflow", description="Sempre falha (teste).")
    async def _falha() -> dict:
        raise montar_erro("not_found", "Não achei o fluxo.")

    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        resultado = await _chamar_em_processo(
            server, "get_workflow", {}, escopo_falso(scopes={"workflows:read"})
        )

    assert resultado.is_error is True
    assert isinstance(ToolError("x"), Exception)
    assert "desfecho=tool_error:not_found" in _linhas_de_auditoria(caplog)[0]
    # O prefixo que o SDK coloca na frente do JSON é removido antes de sair.
    assert json.loads(resultado.content[0].text)["code"] == "not_found"


# ── Borda: Host, Origin e a ordem das recusas ─────────────────────────────────


async def test_host_fora_da_lista_e_421_mesmo_com_pat_valido(ambiente):
    segredo = await _pat(ambiente, ["workflows:read"])
    server = servidor_de_teste()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_mcp), base_url="http://localhost:8000"
        ) as c:
            r = await c.post(
                "/mcp",
                json=_INITIALIZE,
                headers={**_JSON, "Host": "evil.example", "Authorization": f"Bearer {segredo}"},
            )
    assert r.status_code == 421


async def test_origin_presente_e_403_mesmo_com_pat_valido(ambiente):
    """Cliente de navegador só na fase do OAuth — qualquer `Origin` é recusado."""
    segredo = await _pat(ambiente, ["workflows:read"])
    server = servidor_de_teste()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_mcp), base_url="http://localhost:8000"
        ) as c:
            r = await c.post(
                "/mcp",
                json=_INITIALIZE,
                headers={**_JSON, "Origin": "https://x.example", "Authorization": f"Bearer {segredo}"},
            )
    assert r.status_code == 403


async def test_sem_pat_o_401_vem_antes_do_421(ambiente):
    """O middleware é externo ao transporte: quem não se identifica nem chega lá."""
    server = servidor_de_teste()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_mcp), base_url="http://localhost:8000"
        ) as c:
            r = await c.post("/mcp", json=_INITIALIZE, headers={**_JSON, "Host": "evil.example"})
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Bearer")


# ── EscopoEfetivo ─────────────────────────────────────────────────────────────


def test_como_usuario_nunca_carrega_papel_de_administrador():
    """Os services de observabilidade decidem o que mostrar olhando `user.role`.

    Entregar a eles o `User` do banco daria a um PAT o alcance global de um
    administrador — o substituto é sempre `role="user"`.
    """
    escopo = escopo_falso(user_id="usr-admin", username="raiz")
    usuario = escopo.como_usuario()
    assert usuario.role == "user"
    assert usuario.id_hash == "usr-admin"
    assert usuario.username == "raiz"
    assert not hasattr(usuario, "status")


def test_workspace_unico_so_existe_quando_ha_exatamente_um():
    assert escopo_falso(workspace_ids={"ws-1"}).workspace_unico() == "ws-1"
    assert escopo_falso(workspace_ids={"ws-1", "ws-2"}).workspace_unico() is None
    assert escopo_falso(workspace_ids=set()).workspace_unico() is None


def test_escopo_da_chamada_prefere_o_estado_da_request():
    """Com chamadas concorrentes, `request.state` é o canal que não se confunde."""
    from app.mcp.escopo import escopo_da_chamada

    da_request = escopo_falso(token_id="tok-request")
    ficha = ESCOPO_ATUAL.set(escopo_falso(token_id="tok-contextvar"))
    try:
        assert escopo_da_chamada(ctx_falso(da_request)).token_id == "tok-request"
    finally:
        ESCOPO_ATUAL.reset(ficha)


def test_escopo_da_chamada_cai_para_o_contextvar():
    from app.mcp.escopo import escopo_da_chamada

    ficha = ESCOPO_ATUAL.set(escopo_falso(token_id="tok-contextvar"))
    try:
        assert escopo_da_chamada(ctx_falso(None)).token_id == "tok-contextvar"
    finally:
        ESCOPO_ATUAL.reset(ficha)


def test_escopo_da_chamada_sem_identidade_levanta_forbidden():
    from mcp.server.mcpserver.exceptions import ToolError

    from app.mcp.escopo import escopo_da_chamada

    with pytest.raises(ToolError) as exc:
        escopo_da_chamada(ctx_falso(None))
    assert json.loads(str(exc.value))["code"] == "forbidden"


def test_exigir_escopo_lista_todos_os_que_faltam():
    from mcp.server.mcpserver.exceptions import ToolError

    from app.mcp.escopo import exigir_escopo

    escopo = escopo_falso(scopes={"workflows:read"})
    exigir_escopo(escopo, "workflows:read")  # não levanta
    with pytest.raises(ToolError) as exc:
        exigir_escopo(escopo, "workflows:write", "runs:execute")
    corpo = json.loads(str(exc.value))
    assert corpo["code"] == "forbidden_scope"
    assert corpo["missing_scope"] == ["workflows:write", "runs:execute"]


def test_o_hint_de_escopo_diz_quem_alcanca_a_pagina_de_tokens():
    """A página de tokens só abre para o administrador do sistema
    (`web/proxy.ts`), e o token é pessoal: o hint não pode mandar pedir um token
    ao admin (seria o token DELE, agindo em nome dele)."""
    from mcp.server.mcpserver.exceptions import ToolError

    from app.mcp.escopo import exigir_escopo

    with pytest.raises(ToolError) as exc:
        exigir_escopo(escopo_falso(scopes=set()), "drive:write")
    hint = json.loads(str(exc.value))["hint"]
    assert "/settings/tokens" in hint
    assert "administradores" in hint
    assert "peça" not in hint


async def test_o_escopo_chega_a_tool_pelo_estado_da_request(ambiente):
    """Prova o canal primário ponta a ponta, sem o reserva do `ContextVar`.

    A tool lê `ctx.request_context.request.state.escopo` diretamente: é o que
    `escopo_da_chamada` consulta primeiro, e o único canal que não se confunde
    entre chamadas concorrentes.
    """
    segredo = await _pat(ambiente, ["workflows:read"])
    # Instância sem as tools reais: o corpo aqui só devolve a identidade que
    # chegou pelo estado da request (ver `servidor_de_teste`).
    server = ServidorAtlans(
        name="atlans", title="Atlans", instructions=INSTRUCOES, version=VERSAO_MCP,
    )

    @server.tool(name="list_workspaces", description="Devolve a identidade da chamada (teste).")
    async def _quem_sou(ctx: Context) -> dict:
        # A anotação `Context` é o que faz o SDK injetar o contexto em vez de
        # cobrar um argumento do cliente.
        from starlette.requests import Request

        requisicao = ctx.request_context.request
        assert isinstance(requisicao, Request)
        escopo = requisicao.state.escopo
        return {"user_id": escopo.user_id, "token_prefix": escopo.token_prefix}

    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with cliente_mcp(app_mcp, segredo) as cliente:
            resultado = await cliente.call_tool("list_workspaces", {})
    assert resultado.is_error is False, resultado.content
    assert json.loads(resultado.content[0].text)["user_id"] == "usr-1"
