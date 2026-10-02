# app/services/assistente_conversas.py
"""
Persistencia e replay das conversas do assistente da Home.

O laco (`assistente_service.conversar`) e a superficie (`assistente_superficie.HOME`)
nao sabem de banco: quem guarda a conversa e este servico, e a rota
(`assistente_router`) costura os dois. As responsabilidades aqui:

- **CRUD das conversas** — criar, carregar (com portao de dono), listar,
  renomear, apagar (soft), e o `tocar` que carimba `updated_at`/`tokens_total`.
- **Transcrito e persistencia incremental** — `transcrito_de` monta o que o
  modelo recebe (`[{"role", "content"}]`), e `anexar_mensagens` grava as mensagens
  novas com `ordem` contigua. A rota persiste turno a turno pelo gancho
  `ao_fechar_turno`, e nao num blob no fim.
- **Replay** — `quadros_do_replay` reconstroi a conversa nos MESMOS quadros do
  SSE, para o painel reaplicar pelo mesmo caminho de um quadro ao vivo. Duas
  regras de seguranca: um `tool_result` NUNCA sai (e a palavra do servidor,
  nao conteudo de tela), e uma `confirmacao` so reaparece com o token se a chave
  dela ainda existe no Redis (senao seria um botao morto).
- **Confirmacao** — `ler`/`consumir` a chave que o portao da Home ja ESCREVEU
  (PR das superficies). O consumo e um `get`+`delete`: quem apagou executa, quem
  chegou depois perdeu a corrida.
"""
from __future__ import annotations

import json
from contextlib import suppress
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.audit_event import AuditEvent
from app.models.conversa import Conversa, Mensagem
from app.models.models import Workflow
from app.services import assistente_superficie as ag
from app.services import assistente_service as cs

logger = get_logger("app.agente.service")

TAMANHO_DO_TITULO = 60


# ── CRUD ─────────────────────────────────────────────────────────────────────


async def carregar_conversa_da_pessoa(db: AsyncSession, user_id: str, conversa_id: str) -> Conversa:
    """A conversa, se e da pessoa e nao foi apagada. 404 uniforme senao.

    404 e nao 403 de proposito: distinguir "nao existe" de "existe mas nao e sua"
    responderia a pergunta "este id existe?" — que ninguem deveria poder fazer
    varrendo ids. O mesmo criterio da borda do MCP (`resolucao.carregar_workflow`).
    """
    conv = (
        await db.execute(
            select(Conversa).where(
                Conversa.id_hash == conversa_id,
                Conversa.user_id == user_id,
                Conversa.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada.")
    return conv


async def criar_conversa(
    db: AsyncSession,
    *,
    user_id: str,
    workspace_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    titulo: Optional[str] = None,
) -> Conversa:
    conv = Conversa(
        user_id=user_id,
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        titulo=titulo,
        origem="home",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


def titulo_automatico(mensagem: str) -> str:
    """As primeiras palavras da 1a mensagem, ate 60 chars. Titulo por modelo fica
    para depois — este e o barato que ja diz do que a conversa trata."""
    limpo = " ".join((mensagem or "").split())
    return limpo[:TAMANHO_DO_TITULO] if limpo else "Nova conversa"


async def listar_conversas(
    db: AsyncSession, user_id: str, *, limit: int = 50, offset: int = 0
) -> tuple[list[Conversa], int]:
    """As minhas conversas nao apagadas, mais recentemente ativas em cima."""
    base = select(Conversa).where(Conversa.user_id == user_id, Conversa.deleted_at.is_(None))
    total = (
        await db.execute(
            select(func.count(Conversa.id)).where(
                Conversa.user_id == user_id, Conversa.deleted_at.is_(None)
            )
        )
    ).scalar() or 0
    linhas = (
        await db.execute(
            base.order_by(Conversa.updated_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(linhas), int(total)


async def renomear_conversa(db: AsyncSession, user_id: str, conversa_id: str, titulo: str) -> Conversa:
    conv = await carregar_conversa_da_pessoa(db, user_id, conversa_id)
    conv.titulo = titulo
    conv.updated_at = utc_now_naive()
    await db.commit()
    await db.refresh(conv)
    return conv


async def apagar_conversa(db: AsyncSession, user_id: str, conversa_id: str) -> None:
    """Soft delete: some da lista, o historico fica."""
    conv = await carregar_conversa_da_pessoa(db, user_id, conversa_id)
    conv.deleted_at = utc_now_naive()
    await db.commit()


# ── Transcrito e persistencia incremental ────────────────────────────────────


async def transcrito_de(
    db: AsyncSession, conversa_id: str, *, persistir_fecho: bool = False
) -> list[dict[str, Any]]:
    """O que o modelo recebe: `[{"role", "content"}]` na ordem, VERBATIM.

    `blocos` ja esta no formato do projeto (o que o laco grava e o cliente do
    modelo traduz na ida — `app/services/openrouter.py`), entao nao ha conversao
    aqui — so a leitura em ordem.

    `persistir_fecho=True` grava tambem, no banco, o `tool_result` de fecho que
    `_fechar_pendencias` acrescentou. Quem vai RETOMAR a conversa (anexar uma
    mensagem nova depois) precisa disso: fechar so em memoria deixaria o orfao no
    banco e, com a mensagem nova gravada depois dele, o fecho na leitura seguinte
    nao aconteceria mais (`_fechar_pendencias` so olha a ULTIMA mensagem).
    """
    linhas = (
        await db.execute(
            select(Mensagem.papel, Mensagem.blocos)
            .where(Mensagem.conversa_id == conversa_id)
            .order_by(Mensagem.ordem)
        )
    ).all()
    # `_fechar_pendencias` NA LEITURA, e nao so na escrita: o laco so fecha as
    # pendencias no evento `fim`, que nunca acontece quando o gerador e CANCELADO
    # (a pessoa trocou de chat e o fetch abortou no meio de uma ferramenta). O
    # `tool_use` orfao ficava gravado e a API recusava a conversa inteira na
    # retomada ("tool_use ids were found without tool_result blocks"), para
    # sempre. Fechando aqui, o que sai do banco esta sempre bem formado, seja qual
    # for a causa da interrupcao.
    cru = [{"role": papel, "content": blocos} for papel, blocos in linhas]
    fechado = cs._fechar_pendencias(cru)
    if persistir_fecho and len(fechado) > len(cru):
        await anexar_mensagens(
            db, conversa_id, fechado[len(cru):], ordem_inicial=await proxima_ordem(db, conversa_id)
        )
    return fechado


async def proxima_ordem(db: AsyncSession, conversa_id: str) -> int:
    """A proxima `ordem` livre — `MAX(ordem)+1`, nunca a CONTAGEM das linhas.

    A contagem so coincide com a proxima ordem enquanto nada escreve em paralelo.
    Duas abas na mesma conversa liam a mesma contagem e colidiam na UNIQUE
    `uq_mensagens_conversa_ordem` (500 sem tratamento), ou pulavam uma mensagem
    inteira em silencio — deixando `tool_use` e `tool_result` desemparelhados.
    """
    maior = (
        await db.execute(
            select(func.max(Mensagem.ordem)).where(Mensagem.conversa_id == conversa_id)
        )
    ).scalar()
    return 0 if maior is None else int(maior) + 1


async def anexar_mensagens(
    db: AsyncSession,
    conversa_id: str,
    entradas: list[dict[str, Any]],
    *,
    ordem_inicial: int,
    metas: Optional[dict[int, dict[str, Any]]] = None,
) -> int:
    """Grava mensagens no formato do laco (`[{"role", "content"}]`), com `ordem`
    contigua a partir de `ordem_inicial`. Devolve a proxima ordem livre.

    `metas` (opcional) marca uma mensagem pelo indice ABSOLUTO da ordem — usado
    so pela mensagem sintetica de confirmacao, que leva `meta={"tipo":...}`.
    """
    metas = metas or {}
    ordem = ordem_inicial
    for entrada in entradas:
        db.add(
            Mensagem(
                conversa_id=conversa_id,
                ordem=ordem,
                papel=entrada.get("role", "assistant"),
                blocos=entrada.get("content"),
                meta=metas.get(ordem),
            )
        )
        ordem += 1
    if entradas:
        await db.commit()
    return ordem


async def tocar_conversa(
    db: AsyncSession, conversa_id: str, *, tokens_total: Optional[int] = None
) -> None:
    """Carimba `updated_at` (e `tokens_total`, quando dado). Nunca levanta: e
    contabilidade, nao pode derrubar a resposta que ja saiu."""
    conv = (
        await db.execute(select(Conversa).where(Conversa.id_hash == conversa_id))
    ).scalar_one_or_none()
    if conv is None:
        return
    conv.updated_at = utc_now_naive()
    if tokens_total is not None:
        # SOMA, nao atribui: o nome do campo, a docstring do modelo e o
        # `ConversaResumo` prometem o total da CONVERSA. Atribuindo, ele guardava
        # o custo do ultimo turno — e qualquer saida anormal antes do `fim`
        # (trava tomada por outra aba, cota estourada) gravava 0 por cima do
        # acumulado. Quem nao observou o `fim` passa `None` e nao carimba nada.
        conv.tokens_total = int(conv.tokens_total or 0) + int(tokens_total)
    await db.commit()


# ── Confirmacao (a chave ja e escrita pelo portao da Home) ────────────────────


async def ler_confirmacao(
    redis, user_id: str, conversa_id: str, tool_use_id: str
) -> Optional[dict[str, Any]]:
    """O `{token, tool, args, criado_em}` guardado, ou None se expirou/nao existe."""
    if redis is None:
        return None
    try:
        cru = await redis.get(ag.chave_de_confirmacao(user_id, conversa_id, tool_use_id))
    except Exception as exc:  # pragma: no cover - depende do Redis
        logger.warning("Falha ao ler a confirmacao: %s", exc.__class__.__name__)
        return None
    if not cru:
        return None
    try:
        corpo = json.loads(cru)
    except (TypeError, ValueError):  # pragma: no cover - valor corrompido
        return None
    return corpo if isinstance(corpo, dict) else None


async def consumir_confirmacao(
    redis, user_id: str, conversa_id: str, tool_use_id: str
) -> bool:
    """Apaga a chave uma unica vez. True se ESTA chamada apagou (venceu a corrida),
    False se ja tinha sido decidida (delete devolveu 0)."""
    if redis is None:
        return False
    try:
        apagadas = await redis.delete(ag.chave_de_confirmacao(user_id, conversa_id, tool_use_id))
    except Exception as exc:  # pragma: no cover - depende do Redis
        logger.warning("Falha ao consumir a confirmacao: %s", exc.__class__.__name__)
        return False
    return bool(apagadas)


# ── Rastro auditavel do que o assistente ESCREVE ─────────────────────────────


async def _workspace_do_alvo(
    db: AsyncSession, args: Any, workspace_ids: Any = None
) -> Optional[str]:
    """O workspace do fluxo alvo, quando os argumentos carregam um `workflow_id`.

    So resolve o que esta DENTRO do alcance do ator (`workspace_ids`) e nao foi
    apagado. O `workflow_id` vem dos argumentos guardados da confirmacao: sem o
    recorte, um id de outro workspace fazia o `AuditEvent` aterrissar na trilha de
    um workspace do qual a pessoa nao e membro — escrita cross-tenant, ainda que
    so de auditoria. Sem casar, quem chama cai no workspace da conversa.
    """
    ref = args.get("workflow_id") if isinstance(args, dict) else None
    if not ref:
        return None
    alcance = list(workspace_ids or ())
    if not alcance:
        return None
    return (
        await db.execute(
            select(Workflow.workspace_id).where(
                Workflow.id_hash == str(ref),
                Workflow.deleted_at.is_(None),
                Workflow.workspace_id.in_(alcance),
            )
        )
    ).scalar_one_or_none()


async def registrar_acao_confirmada(
    db: AsyncSession,
    *,
    user_id: str,
    conversa_id: str,
    tool: Optional[str],
    args: Any,
    tool_use_id: str,
    decisao: str,
    erro: bool,
    workspace_padrao: Optional[str] = None,
    workspace_ids: Any = None,
) -> None:
    """Grava um `AuditEvent` por acao decidida no cartao de confirmacao.

    Sem isto, o unico registro do que o assistente escreveu era o transcrito em
    `mensagens.blocos` — que a propria pessoa apaga com `DELETE
    /assistente/conversas/{id}`. Um admin investigando arquivos do Drive sumidos nao
    tinha por onde comecar. O rastro cobre justamente o que passa pelo portao: as
    escritas em recurso que ja existia.

    O workspace da linha e o do fluxo alvo, mas so quando ele esta no alcance do
    ator (`workspace_ids`); senao, o da conversa. Ver `_workspace_do_alvo`.

    Nunca levanta: auditoria nao pode derrubar uma acao que ja aconteceu — o
    `logger.exception` e o sinal de que o rastro falhou.
    """
    try:
        workspace_id = (
            await _workspace_do_alvo(db, args, workspace_ids) or workspace_padrao or "desconhecido"
        )
        db.add(
            AuditEvent(
                workspace_id=workspace_id,
                user_id=user_id,
                action=f"assistente.{decisao}",
                resource_type="assistente_tool",
                resource_id=(ag._alvo(args) or tool or "")[:255],
                details={
                    "tool": tool,
                    "argumentos": cs._resumo(args),
                    "conversa_id": conversa_id,
                    "tool_use_id": tool_use_id,
                    "erro": bool(erro),
                },
            )
        )
        await db.commit()
    except Exception:  # pragma: no cover - auditoria e best-effort
        logger.exception("Falha ao auditar a acao do assistente (conversa %s).", conversa_id)
        # Desfaz o flush que falhou: sem isto a sessao fica em `PendingRollback` e
        # derruba a proxima escrita — a auditoria e o ultimo elo, nao pode
        # contaminar quem vem depois.
        with suppress(Exception):
            await db.rollback()


# ── Replay ───────────────────────────────────────────────────────────────────


def _texto_do_tool_result(bloco: dict[str, Any]) -> tuple[str, bool]:
    conteudo = bloco.get("content")
    if isinstance(conteudo, str):
        texto = conteudo
    elif isinstance(conteudo, list):
        texto = "\n".join(
            b.get("text", "") for b in conteudo if isinstance(b, dict) and b.get("text")
        )
    else:
        texto = ""
    return texto, bool(bloco.get("is_error"))


async def _confirmacao_reaberta(
    redis, user_id: str, conversa_id: str, tool_use_id: str
) -> Optional[dict[str, Any]]:
    """O quadro `confirmacao` de uma chamada AINDA PENDENTE — so quando a chave
    do Redis existe. Uma chave sumida (decidida ou expirada) nao vira botao morto."""
    guardado = await ler_confirmacao(redis, user_id, conversa_id, tool_use_id)
    if not guardado:
        return None
    args = guardado.get("args")
    return {
        "tool_use_id": tool_use_id,
        "token": guardado.get("token"),
        "acao": {
            "tool": guardado.get("tool"),
            "argumentos": cs._resumo(args),
            "alvo": ag._alvo(args),
        },
    }


async def quadros_do_replay(
    db: AsyncSession, conversa_id: str, *, redis, user_id: str, tokens_total: int
) -> list[dict[str, Any]]:
    """A conversa reconstruida nos MESMOS quadros do SSE.

    Uma mensagem do usuario vira `usuario`; o texto e o raciocinio do assistente
    viram `texto`/`pensando`; cada `tool_use` vira `ferramenta` (com os argumentos
    RESUMIDOS) e, se ja teve resultado, `ferramenta_fim` mais os quadros da Home
    (`fluxo`/`camada`) daquele resultado — pelo MESMO `quadros_extras` do laco. Um
    `tool_use` ainda sem resultado que tenha confirmacao viva no Redis reabre o
    `confirmacao`. `tool_result` nunca sai. Um `fim` fecha com o total de tokens.
    """
    rows = (
        await db.execute(
            select(Mensagem.papel, Mensagem.blocos, Mensagem.meta)
            .where(Mensagem.conversa_id == conversa_id)
            .order_by(Mensagem.ordem)
        )
    ).all()

    # Mapa tool_use_id -> (texto, erro), colhido dos tool_results (que nao saem).
    resultados: dict[str, tuple[str, bool]] = {}
    for _papel, blocos, _meta in rows:
        if isinstance(blocos, list):
            for b in blocos:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    resultados[b.get("tool_use_id")] = _texto_do_tool_result(b)

    quadros: list[dict[str, Any]] = []
    for papel, blocos, meta in rows:
        if papel == "user":
            # Texto da pessoa (ou a mensagem sintetica de confirmacao, com meta).
            # Lista = tool_results, que NUNCA saem no replay.
            if isinstance(blocos, str):
                dados: dict[str, Any] = {"texto": blocos}
                if meta:
                    dados["meta"] = meta
                quadros.append({"tipo": "usuario", "dados": dados})
            continue
        if not isinstance(blocos, list):
            continue
        for b in blocos:
            if not isinstance(b, dict):
                continue
            tipo = b.get("type")
            if tipo == "text" and b.get("text"):
                quadros.append({"tipo": "texto", "dados": {"texto": b["text"]}})
            elif tipo == "thinking" and b.get("thinking"):
                quadros.append({"tipo": "pensando", "dados": {"texto": b["thinking"]}})
            elif tipo == "tool_use":
                nome = b.get("name")
                args = b.get("input")
                tuid = b.get("id")
                quadros.append(
                    {"tipo": "ferramenta", "dados": {"id": tuid, "nome": nome, "argumentos": cs._resumo(args)}}
                )
                resultado = resultados.get(tuid)
                if resultado is not None:
                    texto_res, deu_erro = resultado
                    quadros.append(
                        {"tipo": "ferramenta_fim", "dados": {"id": tuid, "nome": nome, "erro": deu_erro}}
                    )
                    for evento in ag.HOME.quadros_extras(None, nome, args, texto_res, deu_erro):
                        quadros.append({"tipo": evento.tipo, "dados": evento.dados})
                else:
                    reaberta = await _confirmacao_reaberta(redis, user_id, conversa_id, tuid)
                    if reaberta is not None:
                        quadros.append({"tipo": "confirmacao", "dados": reaberta})

    quadros.append({"tipo": "fim", "dados": {"uso": {"total": int(tokens_total or 0)}, "ok": True}})
    return quadros
