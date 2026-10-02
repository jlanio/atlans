# app/api/routers/assistente_router.py
"""
O assistente da Home — /assistente (conversas persistidas + confirmacao por clique).

Irmao do /assistente/editor, com tres diferencas que moldam o modulo:

- **A superficie e a HOME** (`app/services/assistente_superficie.py`): alcance
  completo, entrega por camada no globo, e confirmacao por clique para o que mexe
  no que ja existia.
- **A conversa e PERSISTIDA no banco** (varias por pessoa, sem prazo), nao no
  Redis efemero do editor. A mensagem do usuario e gravada no handler (antes do
  `return`, enquanto a sessao do request vive); os turnos do assistente, no
  gerador, pelo gancho `ao_fechar_turno` que abre a propria sessao (`infra.sessao`).
- **A confirmacao** e um segundo SSE: valida posse e token, executa os args
  ARMAZENADOS pelo portao (nunca os do clique) e RETOMA o laco no mesmo stream.

A armadilha do `Depends(get_db)` e a mesma do /assistente/editor: a sessao do request
fecha quando o handler RETORNA e o gerador roda depois. Por isso tudo que precisa
do banco no caminho de leitura acontece ANTES do `return`; dai em diante quem abre
sessao e cada gancho, com o ciclo de vida dela mesma.
"""
from __future__ import annotations

import asyncio
import hmac
import json
from contextlib import suppress
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.core.authorization.workflow_access import listar_workspace_ids
from app.core.config import ASSISTENTE_ATIVO
from app.core.rate_limiter import limiter
from app.core.utils.logger import get_logger
from app.mcp import cotas, infra
from app.mcp.escopo import escopo_do_assistente
from app.schemas.assistente import (
    ConversaDetalhe,
    ConversaLista,
    ConversaResumo,
    DecisaoDeConfirmacao,
    Localizacao,
    MensagemDaHome,
    QuadroDoReplay,
    RenomearConversa,
)
from app.api.routers._streaming import com_batimento
from app.schemas.assistente import CotaDoAssistente, EstadoDoAssistente
from app.services import assistente_conversas
from app.services import assistente_superficie as agente
from app.services import assistente_service as assistente
from app.services import teto_do_assistente

logger = get_logger("app.api.agente")

router = APIRouter(
    prefix="/assistente",
    tags=["assistente"],
    dependencies=[Depends(get_current_user)],
)

MOTIVO_DESLIGADO = (
    "O assistente nao esta configurado nesta instalacao. "
    "Defina LLM_API_KEY (ou OPENROUTER_API_KEY) no ambiente da API para liga-lo."
)

# O prefixo das mensagens sinteticas de confirmacao — a guarda que o recusa na
# entrada (`agente.parece_sintetica`), o texto que o servidor grava
# (`agente.MENSAGEM_CONFIRMADA`/`MENSAGEM_RECUSADA`) e o que o prompt ensina o
# modelo a reconhecer vivem os tres em `assistente_superficie`, numa grafia so.


def _exigir_ligado() -> None:
    if not ASSISTENTE_ATIVO:
        raise HTTPException(status_code=503, detail=MOTIVO_DESLIGADO)


def _quadro(evento: assistente.Evento) -> bytes:
    """Um `Evento` virando quadro SSE (`event:`/`data:` JSON, datas em ISO)."""
    corpo = json.dumps(evento.dados, ensure_ascii=False, default=str)
    return f"event: {evento.tipo}\ndata: {corpo}\n\n".encode("utf-8")


def _corpo_do_erro(exc: ToolError) -> dict:
    try:
        corpo = json.loads(str(exc))
    except (TypeError, ValueError):
        return {"code": "recusado", "message": str(exc)}
    return corpo if isinstance(corpo, dict) else {"code": "recusado", "message": str(exc)}


def _resumo_da_conversa(conv) -> ConversaResumo:
    return ConversaResumo(
        id=conv.id_hash,
        titulo=conv.titulo,
        workflow_id=conv.workflow_id,
        tokens_total=conv.tokens_total or 0,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def _chave_da_trava(user_id: str, conversa_id: str) -> str:
    return f"agente:trava:{user_id}:{conversa_id}"


def _workspace_extra(workspace_id: str | None) -> str | None:
    if not workspace_id:
        return None
    return f"Workspace preferido para os fluxos que voce criar: {workspace_id}."


def _localizacao_extra(loc: Localizacao | None) -> str | None:
    if loc is None:
        return None
    precisao = f" (precisao ~{loc.precisao_m:.0f} m)" if loc.precisao_m is not None else ""
    return (
        f"Localizacao atual da pessoa: {loc.lat:.4f}, {loc.lon:.4f}{precisao}. "
        'Use como referencia para pedidos relativos ("perto de mim", "num raio de '
        'N km"); nao repita a coordenada na resposta salvo se ajudar.'
    )


# O nome de cada idioma na instrucao que sobrepoe o padrao da instalacao. O
# portugues nao entra: e o padrao, e o prompt dele fica byte a byte o de sempre.
_NOME_DO_IDIOMA = {"en": "ingles (English)", "es": "espanhol (espanol)"}


def _idioma_extra(idioma: str | None) -> str | None:
    """A tela da pessoa em outro idioma: a resposta e o raciocinio vao nele.

    Vai no bloco EXTRA (nao cacheado), depois da regra de idioma do sistema — e
    diz explicitamente que a substitui, para o modelo nao ficar entre as duas.
    """
    nome = _NOME_DO_IDIOMA.get(idioma or "")
    if not nome:
        return None
    return (
        f"A tela desta pessoa esta em {nome}. Responda e raciocine em {nome}, "
        "inclusive nas respostas rapidas que sugerir — isto substitui a regra de "
        "idioma acima."
    )


def _instrucoes_extras(
    workspace_id: str | None, localizacao: Localizacao | None, idioma: str | None = None
) -> str | None:
    """Junta os extras opcionais do system prompt numa string so — ou None.

    Cada parte (workspace preferido, localizacao atual, idioma da tela) pode
    faltar. Com nenhuma, devolve None: o mesmo no-op de sempre (`montar_sistema`
    nao anexa bloco). Com uma ou mais, junta por linha em branco, na ordem em que
    o modelo as le.
    """
    partes = [
        p
        for p in (_workspace_extra(workspace_id), _localizacao_extra(localizacao), _idioma_extra(idioma))
        if p
    ]
    return "\n\n".join(partes) if partes else None


def _workspace_valido(pedido: str | None, workspace_ids) -> str | None:
    """O `workspace_id` do cliente, so se for mesmo um workspace da pessoa.

    O valor vira texto do SYSTEM prompt (`_workspace_extra`), fora do envelope
    `untrusted_data`. Sem conferir, um cliente com o JWT da pessoa mandava
    instrucao livre de ate 64 chars para dentro do prompt — e gravava um
    `workspace_id` que podia nem ser dela.
    """
    if not pedido:
        return None
    return pedido if pedido in set(workspace_ids or ()) else None


# ── Persistencia incremental (nos ganchos, sessao propria) ───────────────────


class _Cursor:
    """Quantos itens DESTA lista em memoria ja foram gravados.

    Antes, o indice vinha da CONTAGEM do banco (`conversa[ja:]` com
    `ja = contar_mensagens()`), invariante que so vale se as linhas do banco forem
    exatamente `conversa[0:ja]`. Bastava outra aba gravar na mesma conversa para
    a contagem adiantar e uma mensagem inteira do assistente ser pulada em
    silencio — deixando `tool_use` e `tool_result` desemparelhados no banco. O
    cursor e por STREAM: so conta o que ESTE stream escreveu.
    """

    __slots__ = ("ja",)

    def __init__(self, ja: int = 0) -> None:
        self.ja = ja


async def _persistir_turno(conversa_id: str, conversa: list[dict], cursor: _Cursor) -> None:
    """Grava as mensagens que este stream ainda nao gravou."""
    if len(conversa) <= cursor.ja:
        return
    novas = list(conversa[cursor.ja:])
    try:
        async with infra.sessao() as db:
            await assistente_conversas.anexar_mensagens(
                db,
                conversa_id,
                novas,
                ordem_inicial=await assistente_conversas.proxima_ordem(db, conversa_id),
            )
        # So avanca DEPOIS do commit: uma falha deixa as mesmas mensagens
        # pendentes para a proxima tentativa, em vez de as perder.
        cursor.ja += len(novas)
    except Exception:  # pragma: no cover - persistir nao pode derrubar a resposta
        logger.exception("Falha ao persistir turno (conversa %s).", conversa_id)


async def _fechar_persistencia(
    conversa_id: str,
    transcrito_final: list[dict],
    cursor: _Cursor,
    tokens_total: int | None,
) -> None:
    """No fim: grava o que sobrou (pendencias fechadas) e carimba tokens/updated_at.

    `tokens_total=None` quando o evento `fim` nunca chegou — e ai nao se carimba
    nada, em vez de somar 0 (ou, como antes, zerar o acumulado da conversa).
    """
    try:
        await _persistir_turno(conversa_id, transcrito_final, cursor)
        async with infra.sessao() as db:
            await assistente_conversas.tocar_conversa(db, conversa_id, tokens_total=tokens_total)
    except Exception:  # pragma: no cover
        logger.exception("Falha ao fechar a persistencia (conversa %s).", conversa_id)


async def _fechar_protegido(
    conversa_id: str,
    transcrito_final: list[dict],
    cursor: _Cursor,
    tokens_total: int | None,
) -> None:
    """`_fechar_persistencia` blindado contra o CANCELAMENTO do gerador.

    Quando o cliente desconecta, o `finally` roda com o cancelamento pendente e o
    primeiro `await` dentro dele levantaria `CancelledError` antes de qualquer
    escrita. O `shield` deixa a tarefa terminar mesmo assim.
    """
    tarefa = asyncio.ensure_future(
        _fechar_persistencia(conversa_id, transcrito_final, cursor, tokens_total)
    )
    with suppress(asyncio.CancelledError):
        await asyncio.shield(tarefa)


# ── POST /assistente/conversa ────────────────────────────────────────────────────


@router.post("/conversa", summary="Conversar com o assistente da Home (stream)")
@limiter.limit("120/hour")
async def conversar(
    request: Request,
    payload: MensagemDaHome,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _exigir_ligado()
    if agente.parece_sintetica(payload.mensagem):
        # So o servidor escreve esse prefixo (confirmacao). Recusar aqui e o que
        # impede que a pessoa (ou um cliente) o forje.
        raise HTTPException(status_code=422, detail="Mensagem invalida.")

    # ANTES do return: a sessao morre quando este handler sai de cena.
    workspace_ids = await listar_workspace_ids(db, current_user.id_hash)
    escopo = escopo_do_assistente(
        user_id=current_user.id_hash,
        username=getattr(current_user, "username", None),
        workspace_ids=workspace_ids,
    )
    servidor = getattr(request.app.state, "mcp_server", None)
    if servidor is None:  # pragma: no cover - so se o boot mudar
        raise HTTPException(status_code=503, detail="Servidor de ferramentas indisponivel.")

    nova = payload.conversa_id is None
    if nova:
        conv = await assistente_conversas.criar_conversa(
            db,
            user_id=current_user.id_hash,
            workspace_id=_workspace_valido(payload.workspace_id, workspace_ids),
            titulo=assistente_conversas.titulo_automatico(payload.mensagem),
        )
    else:
        conv = await assistente_conversas.carregar_conversa_da_pessoa(
            db, current_user.id_hash, payload.conversa_id
        )

    # O transcrito e a gravacao da mensagem do usuario acontecem DENTRO da trava,
    # no gerador: gravar aqui punha a mensagem no banco antes de a trava sequer
    # ser consultada, e a segunda aba recusada ja tinha corrompido a ordem.
    return StreamingResponse(
        com_batimento(
            _transmitir_conversa(
                escopo=escopo,
                servidor=servidor,
                conversa_id=conv.id_hash,
                titulo=conv.titulo,
                nova=nova,
                mensagem=payload.mensagem,
                workspace_id=conv.workspace_id,
                localizacao=payload.localizacao,
                idioma=payload.idioma,
            )
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _transmitir_conversa(
    *, escopo, servidor, conversa_id, titulo, nova, mensagem, workspace_id, localizacao, idioma=None
) -> AsyncIterator[bytes]:
    redis = infra.redis_ou_none()
    transcrito: list[dict] = []
    transcrito_final: list[dict] = []
    cursor = _Cursor(0)
    tokens_total: int | None = None
    # 1o quadro: a identidade da conversa (o cliente aprende o id de uma nova).
    yield _quadro(assistente.Evento("conversa", {"conversa_id": conversa_id, "titulo": titulo, "nova": nova}))
    try:
        async with assistente.trava_exclusiva(redis, _chave_da_trava(escopo.user_id, conversa_id)):
            # Ler o historico e gravar a mensagem da pessoa, ja sob a trava.
            async with infra.sessao() as db:
                transcrito = await assistente_conversas.transcrito_de(db, conversa_id, persistir_fecho=True)
                await assistente_conversas.anexar_mensagens(
                    db,
                    conversa_id,
                    [{"role": "user", "content": mensagem}],
                    ordem_inicial=await assistente_conversas.proxima_ordem(db, conversa_id),
                )
            transcrito.append({"role": "user", "content": mensagem})
            # Tudo o que esta no transcrito ja foi gravado — o cursor comeca aqui.
            cursor.ja = len(transcrito)
            transcrito_final = list(transcrito)

            async def _hook(conversa: list[dict]) -> None:
                await _persistir_turno(conversa_id, conversa, cursor)

            # O fecho corre SOB a trava: `_fechar_protegido` recomputa
            # `proxima_ordem` e carimba tokens; no `finally` EXTERNO, depois da
            # trava soltar, uma 2a aba que a pegasse nesta janela colidiria no
            # UNIQUE(conversa, ordem) — a mensagem se perdia no except.
            try:
                async for evento in assistente.conversar(
                    escopo=escopo,
                    transcrito=transcrito,
                    servidor=servidor,
                    cliente=assistente.criar_cliente(),
                    redis=redis,
                    superficie=agente.HOME,
                    conversa_id=conversa_id,
                    instrucoes_extras=_instrucoes_extras(workspace_id, localizacao, idioma),
                    ao_fechar_turno=_hook,
                ):
                    if evento.tipo == "fim":
                        transcrito_final = evento.dados.get("transcrito") or transcrito_final
                        tokens_total = (evento.dados.get("uso") or {}).get("total", 0)
                    yield _quadro(evento)
            finally:
                await _fechar_protegido(conversa_id, transcrito_final, cursor, tokens_total)
    except ToolError as exc:
        yield _quadro(assistente.Evento("erro", _corpo_do_erro(exc)))
        yield _quadro(assistente.Evento("fim", {"ok": False}))
    except Exception:
        logger.exception("Assistente quebrou no stream (conversa %s).", conversa_id)
        yield _quadro(assistente.Evento("erro", {"code": "erro_interno", "message": "Algo quebrou do nosso lado."}))
        yield _quadro(assistente.Evento("fim", {"ok": False}))


# ── POST /assistente/conversas/{id}/confirmacoes/{tool_use_id} ───────────────────


@router.post(
    "/conversas/{conversa_id}/confirmacoes/{tool_use_id}",
    summary="Confirmar ou recusar uma acao (stream)",
)
# Mais apertado que os 120/h da conversa, e nao por ser barata: cada clique
# RETOMA o laco inteiro (ate `TETO_DE_VOLTAS` rodadas de modelo), e cada rodada
# pode abrir novas confirmacoes — que gerariam novos POSTs aqui. Sem limiter, o
# caminho inteiro escapava do balde da rota de conversa.
@limiter.limit("60/hour")
async def confirmar(
    conversa_id: str,
    tool_use_id: str,
    payload: DecisaoDeConfirmacao,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _exigir_ligado()
    conv = await assistente_conversas.carregar_conversa_da_pessoa(db, current_user.id_hash, conversa_id)

    redis = infra.redis_ou_none()
    guardado = await assistente_conversas.ler_confirmacao(redis, current_user.id_hash, conv.id_hash, tool_use_id)
    if guardado is None:
        # A chave expirou (15 min) ou nunca existiu — nao ha o que confirmar.
        raise HTTPException(status_code=409, detail="Confirmacao expirada ou ja decidida.")
    # `compare_digest`, nao `==`: o token e um segredo, e a comparacao nao pode
    # vazar por tempo qual caractere bateu.
    if not hmac.compare_digest(str(guardado.get("token", "")), payload.token):
        raise HTTPException(status_code=403, detail="Token de confirmacao invalido.")
    # O CONSUMO (DELETE one-shot) NAO acontece aqui: mora no gerador, sob a trava
    # e imediatamente antes do efeito. Assim, se o cliente cair entre este retorno
    # e o gerador rodar, a confirmacao SOBREVIVE e pode ser refeita — em vez de
    # sumir consumida sem que a acao tenha acontecido. Aqui so se valida (leitura).

    workspace_ids = await listar_workspace_ids(db, current_user.id_hash)
    escopo = escopo_do_assistente(
        user_id=current_user.id_hash,
        username=getattr(current_user, "username", None),
        workspace_ids=workspace_ids,
    )
    servidor = getattr(request.app.state, "mcp_server", None)
    if servidor is None:  # pragma: no cover
        raise HTTPException(status_code=503, detail="Servidor de ferramentas indisponivel.")

    # O transcrito NAO e lido aqui: `persistir_fecho=True` ESCREVE (o tool_result
    # de fecho, via `anexar_mensagens`, que commita) e a trava so e tomada dentro
    # do gerador. A leitura mora la, sob a trava — como na rota irma de conversa.
    return StreamingResponse(
        com_batimento(
            _transmitir_confirmacao(
                escopo=escopo,
                servidor=servidor,
                conversa_id=conv.id_hash,
                tool_use_id=tool_use_id,
                guardado=guardado,
                decisao=payload.decisao,
                workspace_id=conv.workspace_id,
                localizacao=payload.localizacao,
                idioma=payload.idioma,
            )
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _transmitir_confirmacao(
    *, escopo, servidor, conversa_id, tool_use_id, guardado, decisao, workspace_id, localizacao=None,
    idioma=None,
) -> AsyncIterator[bytes]:
    redis = infra.redis_ou_none()
    transcrito: list[dict] = []
    transcrito_final: list[dict] = []
    cursor = _Cursor(0)
    tokens_total: int | None = None
    tool = guardado.get("tool")
    args = guardado.get("args") or {}
    deu_erro = False
    try:
        async with assistente.trava_exclusiva(redis, _chave_da_trava(escopo.user_id, conversa_id)):
            # Consome a confirmacao AQUI — sob a trava e antes de qualquer efeito,
            # nao no handler. Se o cliente cair depois de o handler retornar mas
            # antes disto, a chave SOBREVIVE e a pessoa pode reconfirmar, em vez de
            # a acao confirmada sumir sem repeticao. A trava serializa as abas,
            # entao o DELETE decide a corrida: 0 = outra aba ja consumiu.
            if not await assistente_conversas.consumir_confirmacao(
                redis, escopo.user_id, conversa_id, tool_use_id
            ):
                yield _quadro(
                    assistente.Evento(
                        "erro",
                        {"code": "confirmacao_ja_decidida", "message": "Esta acao ja foi decidida."},
                    )
                )
                yield _quadro(assistente.Evento("fim", {"ok": False}))
                return
            # Ler o historico ja sob a trava. `persistir_fecho=True` GRAVA o
            # tool_result de fecho; fora da trava, uma aba que clicasse num cartao
            # enquanto outra ainda rodava o laco gravava esse fecho sintetico e
            # depois tomava o tool_result verdadeiro por cima — dois resultados
            # para o mesmo `tool_use`, e a API recusando a conversa para sempre.
            async with infra.sessao() as db:
                transcrito = await assistente_conversas.transcrito_de(db, conversa_id, persistir_fecho=True)
            # Tudo o que esta no transcrito ja foi gravado — o cursor comeca aqui.
            cursor.ja = len(transcrito)
            transcrito_final = list(transcrito)

            if decisao == "confirmar":
                # Executa os args ARMAZENADOS, pelo mesmo caminho do laco e sob o
                # escopo do assistente — nunca os args que o cliente mandou no clique.
                fila: list[assistente.Evento] = []

                async def _emitir(evento: assistente.Evento) -> None:
                    fila.append(evento)

                # Com o id da chamada: o quadro `progresso` deste caminho sai
                # com a mesma etiqueta do laço, e o reducer não depende do
                # critério legado "a que está correndo".
                contexto = assistente.ContextoLocal(_emitir, ferramenta_id=tool_use_id)
                yield _quadro(
                    assistente.Evento("ferramenta", {"id": tool_use_id, "nome": tool, "argumentos": assistente._resumo(args)})
                )
                resultado, deu_erro = await assistente.chamar_no_servidor(servidor, escopo, tool, args, contexto)
                while fila:
                    yield _quadro(fila.pop(0))
                yield _quadro(assistente.Evento("ferramenta_fim", {"id": tool_use_id, "nome": tool, "erro": deu_erro}))
                for evento in agente.HOME.quadros_extras(None, tool, args, resultado, deu_erro):
                    yield _quadro(evento)
                sintetica = (
                    f"{agente.MENSAGEM_CONFIRMADA}\n"
                    f"Ferramenta: {tool}\nResultado:\n{resultado}"
                )
            else:
                sintetica = agente.MENSAGEM_RECUSADA

            # Grava a mensagem sintetica (com `meta`) e a anexa ao transcrito, e
            # deixa o RASTRO AUDITAVEL do que o assistente acabou de escrever —
            # o transcrito nao serve de rastro: a pessoa o apaga com DELETE.
            async with infra.sessao() as db:
                ordem = await assistente_conversas.proxima_ordem(db, conversa_id)
                await assistente_conversas.anexar_mensagens(
                    db,
                    conversa_id,
                    [{"role": "user", "content": sintetica}],
                    ordem_inicial=ordem,
                    metas={ordem: {"tipo": "confirmacao", "decisao": decisao, "tool": tool}},
                )
                await assistente_conversas.registrar_acao_confirmada(
                    db,
                    user_id=escopo.user_id,
                    conversa_id=conversa_id,
                    tool=tool,
                    args=args,
                    tool_use_id=tool_use_id,
                    decisao=decisao,
                    erro=deu_erro,
                    workspace_padrao=workspace_id,
                    # O alvo so resolve o workspace dele se for um dos do ATOR:
                    # senao a trilha do assistente aterrissava num workspace do
                    # qual a pessoa nem e membro.
                    workspace_ids=escopo.workspace_ids,
                )
            transcrito.append({"role": "user", "content": sintetica})
            transcrito_final = list(transcrito)
            cursor.ja = len(transcrito)

            # RETOMA o laco no MESMO SSE — o modelo continua a partir do desfecho.
            async def _hook(conversa: list[dict]) -> None:
                await _persistir_turno(conversa_id, conversa, cursor)

            # O fecho corre SOB a trava (como na rota de conversa): fora dela, o
            # `_fechar_protegido` recomputaria `proxima_ordem` numa janela em que
            # outra aba ja teria a trava, colidindo no UNIQUE(conversa, ordem).
            try:
                async for evento in assistente.conversar(
                    escopo=escopo,
                    transcrito=transcrito,
                    servidor=servidor,
                    cliente=assistente.criar_cliente(),
                    redis=redis,
                    superficie=agente.HOME,
                    conversa_id=conversa_id,
                    # A retomada continua sabendo o "perto de mim": o cliente
                    # reenvia a localizacao compartilhada no corpo da decisao
                    # (o servidor nao a guarda — ela vive so no prompt do stream).
                    instrucoes_extras=_instrucoes_extras(workspace_id, localizacao, idioma),
                    ao_fechar_turno=_hook,
                ):
                    if evento.tipo == "fim":
                        transcrito_final = evento.dados.get("transcrito") or transcrito_final
                        tokens_total = (evento.dados.get("uso") or {}).get("total", 0)
                    yield _quadro(evento)
            finally:
                await _fechar_protegido(conversa_id, transcrito_final, cursor, tokens_total)
    except ToolError as exc:
        yield _quadro(assistente.Evento("erro", _corpo_do_erro(exc)))
        yield _quadro(assistente.Evento("fim", {"ok": False}))
    except Exception:
        logger.exception("Confirmacao quebrou no stream (conversa %s).", conversa_id)
        yield _quadro(assistente.Evento("erro", {"code": "erro_interno", "message": "Algo quebrou do nosso lado."}))
        yield _quadro(assistente.Evento("fim", {"ok": False}))


# ── Leitura e gestao das conversas (JSON) ────────────────────────────────────


@router.get("/conversas", response_model=ConversaLista, summary="Minhas conversas")
async def listar(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    linhas, total = await assistente_conversas.listar_conversas(
        db, current_user.id_hash, limit=limit, offset=offset
    )
    return ConversaLista(itens=[_resumo_da_conversa(c) for c in linhas], total=total)


@router.get("/conversas/{conversa_id}", response_model=ConversaDetalhe, summary="Uma conversa (replay)")
async def detalhe(
    conversa_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conv = await assistente_conversas.carregar_conversa_da_pessoa(db, current_user.id_hash, conversa_id)
    quadros = await assistente_conversas.quadros_do_replay(
        db,
        conv.id_hash,
        redis=infra.redis_ou_none(),
        user_id=current_user.id_hash,
        tokens_total=conv.tokens_total or 0,
    )
    return ConversaDetalhe(
        id=conv.id_hash,
        titulo=conv.titulo,
        workflow_id=conv.workflow_id,
        quadros=[QuadroDoReplay(**q) for q in quadros],
    )


@router.patch("/conversas/{conversa_id}", response_model=ConversaResumo, summary="Renomear")
async def renomear(
    conversa_id: str,
    payload: RenomearConversa,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conv = await assistente_conversas.renomear_conversa(db, current_user.id_hash, conversa_id, payload.titulo)
    return _resumo_da_conversa(conv)


@router.delete("/conversas/{conversa_id}", status_code=204, summary="Apagar (soft)")
async def apagar(
    conversa_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await assistente_conversas.apagar_conversa(db, current_user.id_hash, conversa_id)
    return None


@router.get("/estado", response_model=EstadoDoAssistente, summary="O assistente esta disponivel?")
async def estado(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Sem `_exigir_ligado`: responder 503 obrigaria o painel a tratar erro para
    descobrir uma coisa que e so um estado. A cota de tokens e a MESMA do editor
    (`assistente:tokens:{user}`), compartilhada — e por isso o teto tem de sair do
    MESMO lugar la e aqui, senao o mesmo donut mostraria dois tetos conforme a
    tela que o pediu."""
    if not ASSISTENTE_ATIVO:
        return EstadoDoAssistente(ativo=False, motivo=MOTIVO_DESLIGADO)
    redis = infra.redis_ou_none()
    gasto, falta = await cotas.gasto_e_prazo(redis, current_user.id_hash)
    # Os dois juntos, e não o plano seguido do teto dele: com planos, o teto
    # que vale pode ser o CONTRATADO (maior que o vigente, depois de um corte),
    # e mostrar o vigente aqui faria o donut anunciar um limite mais apertado
    # do que a cota de fato aplica — a pessoa pararia de conversar antes da hora.
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
