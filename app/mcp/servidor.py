# app/mcp/servidor.py
"""
O servidor MCP do Atlans: fábrica, guardas na borda das chamadas e o app ASGI.

Duas decisões estruturais moram aqui.

1. `ServidorAtlans` sobrescreve `list_tools` e `call_tool`, que o SDK expõe como
   métodos públicos e chama por `self`. `list_tools` filtra o catálogo pelo
   escopo do token — conforto, para o cliente não gastar chamada tentando uma tool
   que não pode usar. `call_tool` é a garantia de verdade: nenhuma tool roda sem
   passar por escopo e cota, mesmo que o cliente chame um nome que nunca viu na
   lista.

   O default é RECUSAR. Tool sem linha em `GUARDAS` não é chamável e nem sequer
   aparece no catálogo: uma tool nova que o autor esqueceu de declarar falharia
   FECHADA (ninguém a usa e o defeito aparece no log) em vez de rodar sem escopo,
   sem cota e sem papel. O teste de paridade continua existindo como segunda
   linha de defesa — ele avisa em CI, esta regra protege em produção.

2. `create_mcp_server()` é FÁBRICA, não singleton de módulo. `session_manager`
   é um contexto que só pode ser entrado uma vez por instância; com um singleton,
   o segundo teste (ou um segundo `lifespan` num reload) encontraria o gerenciador
   já consumido. Cada processo e cada teste criam a sua instância.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings

from app.core.utils.logger import get_logger
from app.mcp.auth import AutenticacaoPAT
from app.mcp.erros import erro, sem_prefixo_do_sdk
from app.mcp.escopo import ESCOPO_ATUAL, escopo_da_chamada
from app.mcp.guardas import GUARDAS
from app.mcp.instrucoes import INSTRUCOES
from app.mcp.prompts import registrar_prompts
from app.mcp.resources import registrar_resources
from app.mcp.tools import registrar_tools
from app.mcp.tools.base import guarda_da_chamada

# Versão do CONTRATO do servidor (tools, resources, formato das saídas), não do
# Atlans. Uma tool removida fica pelo menos uma versão menor marcada como
# obsoleta antes de sumir — ver docs/mcp.md.
VERSAO_MCP = "1.5.0"

logger = get_logger("app.mcp.servidor")

# Onde o app ASGI fica guardado na instância do servidor — ver `criar_app_mcp`.
_ATRIBUTO_DO_APP = "_app_do_atlans"

# Nomes já denunciados por `list_tools`: o aviso é de defeito de programação
# (tool registrada sem guarda), e repeti-lo a cada `tools/list` afogaria o log.
_SEM_GUARDA_AVISADAS: set[str] = set()


class ServidorAtlans(MCPServer):
    """`MCPServer` com escopo, cota e auditoria em toda chamada de tool."""

    async def list_tools(self):
        """O catálogo filtrado pelo escopo do token da request.

        Sem escopo no `ContextVar` a lista sai com tudo que É chamável: é o caso
        do cliente em processo (`Client(server)`), que não passa pelo middleware.
        Não há perda de segurança — quem decide se a chamada acontece é
        `call_tool`.

        Tool sem guarda declarada sai da lista SEMPRE, com ou sem escopo:
        `call_tool` a recusa, e anunciar o que não se pode chamar só faria o
        cliente gastar chamada para descobrir isso.
        """
        escopo = ESCOPO_ATUAL.get()
        visiveis = []
        for tool in await super().list_tools():
            guarda = GUARDAS.get(tool.name)
            if guarda is None:
                if tool.name not in _SEM_GUARDA_AVISADAS:
                    _SEM_GUARDA_AVISADAS.add(tool.name)
                    logger.error(
                        "Tool %s registrada sem linha em GUARDAS: escondida do catálogo "
                        "e recusada em call_tool.",
                        tool.name,
                    )
                continue
            if escopo is None or guarda.escopo is None or escopo.tem(guarda.escopo):
                visiveis.append(tool)
        return visiveis

    async def call_tool(self, name, arguments, context=None):
        """Escopo → cota → tool → auditoria.

        O mapeamento de exceção de domínio para `ToolError` NÃO acontece aqui: o
        gerenciador de tools do SDK já embrulhou qualquer exceção antes de a
        chamada voltar para cá. Ele mora no decorador de cada tool.
        """
        if name not in GUARDAS:
            # Sem guarda declarada não há escopo a exigir, cota a cobrar nem
            # papel a checar — então não há chamada.
            #
            # `not_found` e não `forbidden` (que prometeria que a tool existe e
            # falta permissão) nem `internal_error` (que acusaria defeito nosso
            # num simples erro de digitação do cliente): do lado de fora, uma
            # tool que não aparece em tools/list e não roda simplesmente não
            # existe. E é o MESMO código nos dois casos — nome que nunca existiu
            # e tool registrada sem a linha da tabela —, para a recusa não virar
            # um oráculo de quais tools a instalação tem escondidas.
            #
            # Só o começo do nome no log: ele vem do cliente, e um nome gigante
            # repetido em laço encheria o log de graça.
            logger.warning("Chamada recusada: %s não tem guarda declarada.", str(name)[:60])
            raise erro(
                "not_found",
                "Ferramenta indisponível neste servidor.",
                "use tools/list para ver o que este token alcança",
            )

        # Fora do bloco cronometrado de propósito: quando a identidade não
        # resolve não há token nem usuário para nomear na linha de auditoria.
        escopo = escopo_da_chamada(context)

        async with guarda_da_chamada(name, escopo):
            try:
                return await super().call_tool(name, arguments, context)
            except ToolError as exc:
                # O SDK prefixa o texto com "Error executing tool <nome>: " ao
                # re-levantar o erro de dentro da tool. Sem tirar o prefixo, o
                # cliente receberia dois formatos: o JSON puro quando a guarda
                # recusa, e o JSON precedido de prosa quando a tool falha.
                limpa = sem_prefixo_do_sdk(str(exc))
                if limpa != str(exc):
                    raise ToolError(limpa) from exc.__cause__
                raise


def hosts_permitidos() -> list[str]:
    """Os `Host` aceitos pelo transporte (defesa contra DNS rebinding).

    Lido a cada chamada, e não no import, para que um ajuste de ambiente (ou um
    teste) valha sem recarregar o módulo.
    """
    from app.core import config

    return list(config.MCP_ALLOWED_HOSTS)


def create_mcp_server() -> ServidorAtlans:
    """Uma instância nova do servidor, com tools, resources e prompts registrados."""
    server = ServidorAtlans(
        name="atlans",
        title="Atlans",
        instructions=INSTRUCOES,
        version=VERSAO_MCP,
    )
    registrar_tools(server)
    registrar_resources(server)
    registrar_prompts(server)
    return server


def criar_app_mcp(server: ServidorAtlans):
    """O app ASGI do `/mcp`: transporte streamable HTTP atrás do middleware de PAT.

    - `streamable_http_path="/mcp"` casa com a rota exata montada em `app.main`,
      sem redirect na URL canônica;
    - `stateless_http=True` para que vários workers uvicorn atendam o mesmo
      cliente sem afinidade de sessão;
    - `json_response=False` é obrigatório: o progresso de uma execução só chega ao
      cliente pelo SSE da própria request;
    - `allowed_origins=[]` recusa qualquer `Origin`. Clientes MCP não-navegador
      não mandam esse cabeçalho; um navegador só entra na fase do OAuth.

    Uma instância tem UM app. `streamable_http_app()` troca o `session_manager`
    do servidor a cada chamada, e o `lifespan` de `app.main` entra no gerenciador
    que existia quando ele subiu: uma segunda chamada deixaria o app servido com
    um gerenciador que ninguém iniciou — toda request responderia erro de sessão.
    Por isso o app criado fica guardado na própria instância e é devolvido de
    novo, em vez de um segundo ser construído em silêncio.
    """
    existente = getattr(server, _ATRIBUTO_DO_APP, None)
    if existente is not None:
        return existente
    app = AutenticacaoPAT(
        server.streamable_http_app(
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=False,
            transport_security=TransportSecuritySettings(
                allowed_hosts=hosts_permitidos(),
                allowed_origins=[],
            ),
        )
    )
    setattr(server, _ATRIBUTO_DO_APP, app)
    return app
