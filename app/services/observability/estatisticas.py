# app/services/observability/estatisticas.py
# Lógica de negócio e consultas de observabilidade extraídas do router.
# Contrato com a web: docs/specs/historico-metricas.md (§3).

from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence

from sqlalchemy import func, select, literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WorkflowRun


# "Duracao tipica" e a mediana das execucoes CONCLUIDAS com duracao positiva:
# falhas, zeros do agendador e orfaos entravam na media antiga e uma execucao
# de 40 min entre cem de 30 s virava "54 s". A janela de 90 dias e a mesma do
# criterio de execucao presa (spec §3.1) e do `typical_seconds` do detalhe.
_TIPICO_DIAS = 90


# Tamanho maximo do `last_error` nos resumos (spec §3.1): a mensagem inteira
# fica no detalhe do run; aqui ela e uma linha da tabela.
_ERRO_RESUMIDO = 200


from app.core.utils.estatistica import percentil_linear
from app.services.observability.escopo import _e_postgres

# ── Percentis ─────────────────────────────────────────────────────────────────

# So execucoes concluidas com duracao positiva entram nos percentis (spec
# §3.1): falha/cancelamento nao dizem quanto o fluxo demora, e `0` e o que o
# agendador grava quando nem chegou a despachar.
_DURACAO_VALIDA = (WorkflowRun.status == "success", WorkflowRun.duration_seconds > 0)


def _colunas_percentil(ps: Sequence[float]) -> list:
    return [
        func.percentile_cont(p).within_group(WorkflowRun.duration_seconds).label(f"p{i}")
        for i, p in enumerate(ps)
    ]


def _arredondar(valor) -> Optional[float]:
    return round(float(valor), 3) if valor is not None else None


async def _percentis(db: AsyncSession, filtros: list, ps: Sequence[float]) -> list[Optional[float]]:
    """Percentis da duracao das execucoes concluidas que passam em `filtros`.

    No PostgreSQL e um `percentile_cont(...) WITHIN GROUP` — uma linha de
    resposta. Fora dele projeta SO a coluna `duration_seconds` do recorte e
    interpola em Python; `filtros` sempre traz a janela, entao o volume e o
    que a tela pede, nunca a tabela.
    """
    if _e_postgres(db):
        row = (await db.execute(
            select(*_colunas_percentil(ps)).where(*_DURACAO_VALIDA, *filtros)
        )).one()
        return [_arredondar(getattr(row, f"p{i}")) for i in range(len(ps))]

    result = await db.execute(
        select(WorkflowRun.duration_seconds).where(*_DURACAO_VALIDA, *filtros)
    )
    valores = [float(v) for v in result.scalars().all() if v is not None]
    return [_arredondar(percentil_linear(valores, p)) for p in ps]


async def _percentis_por(
    db: AsyncSession, coluna, filtros: list, ps: Sequence[float],
) -> dict:
    """`_percentis` agrupado por `coluna` (workflow_hash ou host) —
    `{valor da coluna: [percentis...]}`. Grupos sem execucao concluida nao
    aparecem: quem consulta trata a ausencia como `None`."""
    if _e_postgres(db):
        result = await db.execute(
            select(coluna.label("grupo"), *_colunas_percentil(ps))
            .where(*_DURACAO_VALIDA, *filtros)
            .group_by(coluna)
        )
        return {
            row.grupo: [_arredondar(getattr(row, f"p{i}")) for i in range(len(ps))]
            for row in result.all()
        }

    result = await db.execute(
        select(coluna.label("grupo"), WorkflowRun.duration_seconds)
        .where(*_DURACAO_VALIDA, *filtros)
    )
    grupos: dict = {}
    for row in result.all():
        if row.duration_seconds is not None:
            grupos.setdefault(row.grupo, []).append(float(row.duration_seconds))
    return {g: [_arredondar(percentil_linear(v, p)) for p in ps] for g, v in grupos.items()}


async def _p50_por_workflow(
    db: AsyncSession, workflow_hashes: Iterable[str], now: datetime,
) -> dict[str, Optional[float]]:
    """Mediana dos ultimos 90 dias, por workflow — o `typical_seconds` da spec.
    Sem filtro de workspace de proposito: e um numero agregado do workflow, e
    quem chega aqui ja teve o acesso ao workflow (ou ao run) verificado."""
    hashes = [h for h in set(workflow_hashes) if isinstance(h, str)]
    if not hashes:
        return {}
    since = now - timedelta(days=_TIPICO_DIAS)
    grupos = await _percentis_por(
        db, WorkflowRun.workflow_hash,
        [WorkflowRun.workflow_hash.in_(hashes), WorkflowRun.start_time >= since],
        [0.5],
    )
    return {h: v[0] for h, v in grupos.items()}


async def _ultima_execucao_por_workflow(
    db: AsyncSession, filtros: list, workflow_hashes: Optional[Iterable[str]] = None,
    *, com_erro: bool = True,
) -> dict[str, object]:
    """Ultima execucao (status, erro, categoria, inicio) de cada workflow que
    passa em `filtros`, numa consulta so.

    ROW_NUMBER() OVER (PARTITION BY workflow_hash ORDER BY start_time DESC)
    compila igual no PostgreSQL e no SQLite (>= 3.25), entao nao ha dois
    caminhos para manter. `filtros` sempre traz a janela e o escopo — sem
    eles a funcao de janela varreria a tabela inteira.

    `com_erro=False` deixa `error_message` fora da projecao: a chamada que so
    quer status e inicio da ultima execucao ordena a janela inteira, e o texto
    do erro e a coluna mais larga da tabela — carrega-lo para descartar e o
    custo que nao vale pagar em instalacao grande.
    """
    condicoes = list(filtros)
    if workflow_hashes is not None:
        hashes = [h for h in set(workflow_hashes) if isinstance(h, str)]
        if not hashes:
            return {}
        condicoes.append(WorkflowRun.workflow_hash.in_(hashes))

    posicao = (
        func.row_number()
        .over(
            partition_by=WorkflowRun.workflow_hash,
            order_by=(WorkflowRun.start_time.desc(), WorkflowRun.id.desc()),
        )
        .label("posicao")
    )
    colunas_de_erro = (
        [WorkflowRun.error_message, WorkflowRun.error_category] if com_erro
        else [literal(None).label("error_message"), literal(None).label("error_category")]
    )
    sub = (
        select(
            WorkflowRun.workflow_hash,
            WorkflowRun.status,
            *colunas_de_erro,
            WorkflowRun.start_time,
            posicao,
        )
        .where(*condicoes)
        .subquery("ultimas")
    )
    result = await db.execute(select(sub).where(sub.c.posicao == 1))
    return {row.workflow_hash: row for row in result.all()}


def _resumir_erro(texto: Optional[str]) -> Optional[str]:
    if not texto:
        return None
    texto = texto.strip()
    return texto if len(texto) <= _ERRO_RESUMIDO else texto[: _ERRO_RESUMIDO - 1].rstrip() + "…"


