# app/mcp/auth.py
"""
`AutenticacaoPAT` — a borda do `/mcp`.

Middleware ASGI puro (não `BaseHTTPMiddleware`) na frente do app do SDK. Puro
porque o transporte streamable HTTP devolve SSE de longa duração, e o
`BaseHTTPMiddleware` do Starlette envolve a resposta numa task com fila — o
caminho pelo qual o progresso de uma execução chegaria ao cliente com atraso ou
nem chegaria. Aqui a única coisa que acontece é: valida, decora o `scope`,
repassa.

O que este módulo garante (e é a única linha entre um token e os dados):
- token NUNCA em query string — URL vaza em log de proxy, histórico e Referer.
  Se o cliente mandar, a resposta é 401 sem sequer olhar o valor;
- só `Authorization: Bearer atl_pat_…`. JWT de sessão não vale aqui: o `/mcp`
  fica fora das dependencies globais de propósito, e aceitar um JWT daria a um
  cliente a sessão inteira do navegador;
- toda recusa devolve a MESMA mensagem. Distinguir "não existe" de "expirou" de
  "revogado" transformaria o endpoint num oráculo de tokens válidos;
- o escopo resolvido vai para dois lugares: `scope["state"]["escopo"]` (o que as
  tools leem pelo `ctx`) e o `ContextVar` (o único canal que chega ao
  `list_tools`, que não recebe `ctx`), com reset garantido no `finally`;
- `GET /mcp` é recusado com 405 antes de qualquer ida ao banco. Com
  `stateless_http=True` não existe stream de servidor para entregar: o GET
  abriria um SSE que nunca manda nada e nunca fecha, e um token só de leitura
  prenderia uma conexão de worker por chamada. O 405 com `Allow: POST` é a
  resposta que a própria especificação do transporte prevê para o servidor que
  não oferece o canal de servidor→cliente, e todo cliente MCP sabe lê-la.
"""
from __future__ import annotations

import json
from urllib.parse import parse_qs

from app.core.authorization.pat import e_segredo_pat
from app.core.authorization.workflow_access import listar_workspace_ids
from app.core.utils.logger import get_logger
from app.mcp import infra
from app.mcp.escopo import ESCOPO_ATUAL, EscopoEfetivo
from app.services import api_token_service

logger = get_logger("app.mcp.auth")

REALM = "atlans-mcp"

# Uma frase só, para qualquer motivo de recusa — ver a nota do módulo.
#
# O token é PESSOAL: cada conta cria, lista e revoga só os seus
# (`api_token_service`), e ele age em nome de quem o criou. E `/settings/tokens`,
# como toda página fora da Home, devolve `/` a quem não é admin (`web/proxy.ts`):
# hoje só o administrador do sistema consegue criar token. A mensagem diz isso,
# sem mandar ninguém "pedir um token ao admin" — ele só cria token da própria
# conta, e entregá-lo seria deixar outra pessoa agir em nome dele.
MENSAGEM_RECUSA = (
    "Token pessoal de acesso ausente ou inválido. Use "
    "Authorization: Bearer atl_pat_… (cada pessoa cria o próprio token em "
    "/settings/tokens, hoje página só de administradores do sistema)."
)

# Nomes que clientes distraídos usam para passar o token na URL.
PARAMETROS_DE_TOKEN = ("access_token", "token")


class AutenticacaoPAT:
    """Embrulha o app ASGI do MCP exigindo um PAT válido."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        tipo = scope.get("type")
        if tipo == "lifespan":
            # O ciclo de vida do transporte NÃO passa por aqui para dentro. Quem
            # entra em `session_manager.run()` é o `lifespan` de `app.main`, uma
            # vez por processo; repassar o evento ao app do SDK faria um segundo
            # `run()` no mesmo gerenciador — que é um contexto de uso único — e a
            # falha apareceria só no primeiro request. Respondemos o protocolo e
            # avisamos, para que um refactor que troque a rota por um mount seja
            # percebido no log em vez de na madrugada.
            logger.warning(
                "O app do MCP recebeu lifespan: o gerenciador de sessões é iniciado "
                "por app.main, não aqui."
            )
            await _atender_lifespan(receive, send)
            return

        if tipo != "http":
            # `websocket`: o MCP não expõe nenhum, e não há o que autenticar.
            await self.app(scope, receive, send)
            return

        if scope.get("method") == "GET":
            # Antes do banco de propósito — ver a nota do módulo.
            await _recusar_metodo(send)
            return

        if _tem_token_na_query(scope.get("query_string", b"")):
            logger.warning("Tentativa de autenticar no MCP com token na query string — recusada.")
            await _recusar(send)
            return

        segredo = _segredo_do_header(scope.get("headers") or [])
        if not e_segredo_pat(segredo):
            await _recusar(send)
            return

        async with infra.sessao() as db:
            par = await api_token_service.resolver(db, segredo)
            if par is None:
                # Formato certo, token não resolve: o `error="invalid_token"` do
                # RFC 6750 ajuda o cliente a saber que precisa de OUTRO token, e
                # não de mais um cabeçalho.
                await _recusar(send, invalido=True)
                return
            token, usuario = par
            do_usuario = set(await listar_workspace_ids(db, usuario.id_hash))
            # `workspace_ids` NULL = "todos os workspaces do usuário, inclusive
            # os que ele entrar depois". Tratar NULL como lista vazia tiraria do
            # token justamente o alcance que o dono escolheu na tela.
            alcance_do_token = token.workspace_ids
            todos = alcance_do_token is None
            alcance = do_usuario if todos else do_usuario & set(alcance_do_token)
            escopo = EscopoEfetivo(
                user_id=usuario.id_hash,
                username=getattr(usuario, "username", None),
                token_id=token.id_hash,
                token_prefix=token.token_prefix,
                scopes=frozenset(token.scopes or ()),
                workspace_ids=frozenset(alcance),
                todos_os_workspaces=todos,
            )
            redis = infra.redis_ou_none()
            if redis is not None:
                # Best-effort com throttle de 60 s no próprio service; nunca
                # levanta, e sem Redis simplesmente não carimba.
                await api_token_service.marcar_uso(db, redis, token)

        scope.setdefault("state", {})["escopo"] = escopo
        ficha = ESCOPO_ATUAL.set(escopo)
        try:
            await self.app(scope, receive, send)
        finally:
            ESCOPO_ATUAL.reset(ficha)


async def _atender_lifespan(receive, send) -> None:
    """Responde o protocolo de ciclo de vida sem repassá-lo ao app do SDK."""
    while True:
        mensagem = await receive()
        tipo = mensagem.get("type")
        if tipo == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif tipo == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return
        else:  # pragma: no cover - o protocolo só define os dois eventos acima
            return


def _tem_token_na_query(query_string: bytes) -> bool:
    """True se a URL carrega `access_token=`/`token=` — recusa antes de ler o valor."""
    if not query_string:
        return False
    try:
        parametros = parse_qs(query_string.decode("latin-1"))
    except Exception:  # pragma: no cover - query string ilegível já basta para recusar
        return True
    return any(nome in parametros for nome in PARAMETROS_DE_TOKEN)


def _segredo_do_header(headers) -> str | None:
    """O segredo do `Authorization: Bearer …`, ou None se o cabeçalho não serve."""
    for nome, valor in headers:
        if nome.lower() != b"authorization":
            continue
        try:
            texto = valor.decode("latin-1").strip()
        except Exception:  # pragma: no cover - cabeçalho ilegível
            return None
        esquema, _, resto = texto.partition(" ")
        if esquema.lower() != "bearer":
            return None
        return resto.strip() or None
    return None


async def _recusar_metodo(send) -> None:
    """405 com `Allow: POST` — o método não serve, seja qual for o token."""
    corpo = json.dumps(
        {
            "error": "method_not_allowed",
            "message": (
                "O /mcp aceita apenas POST. Este servidor não abre stream de "
                "servidor→cliente: o progresso viaja no SSE da própria chamada."
            ),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 405,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(corpo)).encode("ascii")),
                (b"allow", b"POST"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": corpo})


async def _recusar(send, *, invalido: bool = False) -> None:
    """401 em JSON, com o desafio que os clientes MCP sabem ler."""
    corpo = json.dumps(
        {"error": "unauthorized", "message": MENSAGEM_RECUSA}, ensure_ascii=False
    ).encode("utf-8")
    desafio = f'Bearer realm="{REALM}"'
    if invalido:
        desafio += ', error="invalid_token"'
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(corpo)).encode("ascii")),
                (b"www-authenticate", desafio.encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": corpo})
