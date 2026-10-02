# app/api/routers/assistente/editor_router.py
"""
O assistente no editor — /assistente/editor.

Três rotas, e a primeira é a única que faz trabalho: `POST /conversa` devolve a
resposta como `text/event-stream`, quadro a quadro, enquanto o laço de
ferramentas roda contra o servidor MCP deste processo.

**Por que um router normal, e não um `add_route` por fora como o `/mcp`.** O
`/mcp` sai da pilha de middleware porque o transporte dele tem exigências
próprias. Aqui a pergunta era se SSE sobrevive ao `SecurityHeadersMiddleware`
(um `BaseHTTPMiddleware`) e ao GZip — e a resposta foi **medida**, com uvicorn
num socket de verdade: os quadros chegam espaçados, os cabeçalhos de segurança
são aplicados, e o GZip do Starlette 1.6 exclui `text/event-stream` por dentro.
Não há motivo para escapar da pilha.

**A armadilha do `Depends(get_db)`.** A sessão do request fecha quando o handler
RETORNA, e o gerador do `StreamingResponse` roda depois disso. Nada que precise
de banco pode acontecer lá dentro. Por isso os workspaces são resolvidos ANTES
do `return`; daí em diante quem abre sessão é cada ferramenta, pelo
`infra.sessao` do MCP, com o ciclo de vida dela mesma.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.api.routers._streaming import com_batimento
from app.core.authorization.workflow_access import listar_workspace_ids
from app.core.config import ASSISTENTE_ATIVO
from app.core.rate_limiter import limiter
from app.core.utils.logger import get_logger
from app.mcp import cotas, infra
from app.schemas.assistente import CotaDoAssistente, EstadoDoAssistente, MensagemDoEditor
from app.services import assistente_service as assistente
from app.services import teto_do_assistente

logger = get_logger("app.api.assistente")

router = APIRouter(
    prefix="/assistente/editor",
    tags=["assistente"],
    dependencies=[Depends(get_current_user)],
)

MOTIVO_DESLIGADO = (
    "O assistente não está configurado nesta instalação. "
    "Defina LLM_API_KEY (ou OPENROUTER_API_KEY) no ambiente da API para ligá-lo."
)


def _exigir_ligado() -> None:
    """503, e não 404: quem instalou sem a chave precisa saber que o recurso existe."""
    if not ASSISTENTE_ATIVO:
        raise HTTPException(status_code=503, detail=MOTIVO_DESLIGADO)


def _quadro(evento: assistente.Evento) -> bytes:
    """Um `Evento` virando quadro SSE.

    `event:` nomeado em vez de tudo num canal só: o painel assina por tipo e não
    precisa desempacotar um envelope para saber se aquilo é texto, progresso ou
    o fim da conversa.
    """
    corpo = json.dumps(evento.dados, ensure_ascii=False, default=str)
    return f"event: {evento.tipo}\ndata: {corpo}\n\n".encode("utf-8")


@router.post("/conversa", summary="Conversar com o assistente (stream)")
@limiter.limit("60/hour")
async def conversar(
    request: Request,
    payload: MensagemDoEditor,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manda uma mensagem e recebe a resposta em `text/event-stream`.

    O histórico daquele fluxo é carregado e salvo pelo servidor: o cliente manda
    só a mensagem nova. Ver a nota 2 de `assistente_service.py` — um transcrito
    vindo do navegador permitiria forjar resultado de ferramenta.
    """
    _exigir_ligado()

    # ANTES do `return`: a sessão morre quando este handler sai de cena.
    workspace_ids = await listar_workspace_ids(db, current_user.id_hash)
    escopo = assistente.escopo_do_editor_para(current_user, workspace_ids)

    servidor = getattr(request.app.state, "mcp_server", None)
    if servidor is None:  # pragma: no cover - só se o boot mudar
        raise HTTPException(status_code=503, detail="Servidor de ferramentas indisponível.")

    return StreamingResponse(
        # `com_batimento`: um `: ping` a cada 15 s de silencio, senao um turno
        # longo (montar e rodar um fluxo) fica minutos mudo e o proxy derruba o
        # SSE antes do primeiro quadro. Mesmo batimento que o assistente da Home.
        com_batimento(
            _transmitir(
                escopo=escopo,
                servidor=servidor,
                workflow_id=payload.workflow_id,
                mensagem=payload.mensagem,
            )
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Desliga o buffer de proxy que exista no caminho. O Traefik não
            # bufferiza por padrão, mas o cabeçalho é barato e o dia em que
            # alguém puser um nginx na frente ele já está aqui.
            "X-Accel-Buffering": "no",
        },
    )


async def _transmitir(*, escopo, servidor, workflow_id, mensagem) -> AsyncIterator[bytes]:
    """O gerador do SSE: trava, carrega, conversa, salva — e salva mesmo se der errado.

    O `finally` do `salvar` é o que faz fechar a aba no meio da resposta não
    apagar a conversa. A cota já está protegida sem ele: `conversar` cobra
    depois de CADA chamada ao modelo, dentro do laço, e não no fim.
    """
    redis = infra.redis_ou_none()
    transcrito: list[dict] = []
    try:
        async with assistente.conversa_exclusiva(redis, escopo.user_id, workflow_id):
            transcrito = await assistente.carregar_conversa(redis, escopo.user_id, workflow_id)
            transcrito.append({"role": "user", "content": mensagem})
            try:
                async for evento in assistente.conversar(
                    escopo=escopo,
                    transcrito=transcrito,
                    servidor=servidor,
                    cliente=assistente.criar_cliente(),
                    redis=redis,
                ):
                    if evento.tipo == "fim":
                        transcrito = evento.dados.get("transcrito") or transcrito
                    yield _quadro(evento)
            finally:
                # Blindado contra o CANCELAMENTO do gerador: quando o cliente
                # fecha a aba no meio da resposta, o `finally` roda com o
                # cancelamento pendente e um `await` cru levantaria
                # `CancelledError` antes de gravar — o turno inteiro se perderia.
                # O `shield` deixa a gravacao terminar mesmo assim (mesmo padrao
                # do `_fechar_protegido` do assistente da Home).
                gravacao = asyncio.ensure_future(
                    assistente.salvar_conversa(redis, escopo.user_id, workflow_id, transcrito)
                )
                with suppress(asyncio.CancelledError):
                    await asyncio.shield(gravacao)
    except ToolError as exc:
        # Recusa declarada (cota estourada, conversa em andamento). Vai como
        # quadro de erro, e não como status HTTP, porque a resposta já começou —
        # e porque assim o painel tem UM caminho de erro só.
        yield _quadro(assistente.Evento("erro", _corpo_do_erro(exc)))
        yield _quadro(assistente.Evento("fim", {"transcrito": transcrito, "ok": False}))
    except Exception:
        logger.exception("Assistente quebrou no stream (usuário %s).", escopo.user_id)
        yield _quadro(
            assistente.Evento(
                "erro",
                {"code": "erro_interno", "message": "Algo quebrou do nosso lado."},
            )
        )
        yield _quadro(assistente.Evento("fim", {"transcrito": transcrito, "ok": False}))


def _corpo_do_erro(exc: ToolError) -> dict:
    """O JSON que `erro()` monta, ou um envelope equivalente quando não for JSON."""
    try:
        corpo = json.loads(str(exc))
    except (TypeError, ValueError):
        return {"code": "recusado", "message": str(exc)}
    return corpo if isinstance(corpo, dict) else {"code": "recusado", "message": str(exc)}


@router.get("/estado", response_model=EstadoDoAssistente, summary="O assistente está disponível?")
async def estado(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """O que o painel consulta antes de aparecer na tela.

    Não usa `_exigir_ligado`: responder 503 aqui obrigaria o painel a tratar
    erro para descobrir uma coisa que é só um estado.
    """
    if not ASSISTENTE_ATIVO:
        return EstadoDoAssistente(ativo=False, motivo=MOTIVO_DESLIGADO)

    redis = infra.redis_ou_none()
    gasto, falta = await cotas.gasto_e_prazo(redis, current_user.id_hash)
    # O teto pode ser do PLANO (com a extensao de planos). Este handler e comum
    # (sem gerador SSE), entao a sessao do `Depends` vive ate o `return` e pode
    # ser reusada — o laco da conversa, que nao tem sessao, e que abre a propria.
    # Os dois juntos, e não o plano seguido do teto dele: o teto que vale pode
    # ser o CONTRATADO (maior que o vigente, depois de um corte), e mostrar o
    # vigente aqui faria o donut anunciar um limite mais apertado do que a cota
    # de fato aplica — a pessoa pararia de conversar antes da hora.
    plano, teto = await teto_do_assistente.plano_e_teto(
        current_user.id_hash, db=db, redis=redis
    )
    return EstadoDoAssistente(
        ativo=True,
        plano=plano,
        assinaturas_ativas=teto_do_assistente.assinaturas_ativas(),
        cota=CotaDoAssistente(
            gasto=gasto,
            teto=teto,
            reabre_em_segundos=falta,
        ),
    )


@router.delete("/conversa", status_code=204, summary="Esquecer a conversa deste fluxo")
async def esquecer(
    workflow_id: str | None = None,
    current_user=Depends(get_current_user),
):
    """Recomeça do zero naquele fluxo. Não apaga fluxo nenhum — só o histórico."""
    _exigir_ligado()
    await assistente.esquecer_conversa(infra.redis_ou_none(), current_user.id_hash, workflow_id)
    return None
