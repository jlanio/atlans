# app/services/fechamento_de_run.py
"""
Fechar um run pelo SERVIDOR — sem job_result do executor.

Nove caminhos fecham um run assim: o despacho (nenhum executor aceitou, a
barreira de isolamento, uma exceção no meio), o cancelamento (run ainda na
fila, ou com o executor fora do ar) e os vigias de `executor_ws/orfaos.py`
(executor que sumiu, run preso em 'pending' sem entrega, job descartado no
relay, run perdido na reconciliação do inventário). Cada um tinha a sua cópia, e
elas divergiram: os do despacho atribuíam `run.status` e gravavam por PK — o
"segundo escritor" que os outros evitavam — e não publicavam a conclusão. A
regra mora aqui, igual para todos:

1. UPDATE condicional (compare-and-swap) no status: só fecha o run que ainda
   está num dos estados de `de` (e, com `host`, no executor dado). O desfecho
   que outro escritor gravou antes — o job_result do executor, o cancelamento
   do usuário, outro worker — não é sobrescrito, e o run não é contado duas
   vezes.
2. Espelho no objeto sem sujá-lo (`set_committed_value`): uma atribuição comum
   faria o próximo flush reemitir o status por PK, que é justamente o segundo
   escritor.
3. Contabilização no usage_daily (`account_terminal_run`): estes runs nunca
   passam pela fila run_results.
4. `__workflow_complete__` (`publicar_conclusao`) para o painel aberto, uma vez
   por run — só quem venceu o UPDATE publica. Best-effort: o run já está
   fechado no banco, e o painel também o descobre ao reabrir.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import inspect, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.core import run_result_consumer
from app.core.utils.logger import get_logger
from app.models.workflow_run import WorkflowRun
from app.services import run_events_service

logger = get_logger(__name__)

# Os estados de quem ainda não terminou.
ABERTOS = ("pending", "running")

# O `extra` do evento de conclusão, na taxonomia do flow, para quem falhou sem
# culpa do conteúdo (executor sumiu, envio não chegou, nenhum executor aceitou):
# repetir a execução é seguro — o painel oferece o "tentar de novo".
REPETIVEL = {"error_category": "transient", "retryable": True}


async def fechar_runs(
    db: AsyncSession,
    runs: Iterable[WorkflowRun | str],
    *,
    de: tuple[str, ...],
    para: str,
    mensagem: str,
    categoria: str | None,
    host: str | None = None,
    duracao: bool = False,
    extra: dict | None = None,
) -> list[WorkflowRun]:
    """Fecha como `para` os `runs` (objetos da sessão ou task_ids) que ainda
    estão em `de`; devolve os que ESTA chamada fechou, já espelhados.

    `categoria` vai para `error_category` (None num cancelamento — cancelar não
    é falhar). `duracao` grava `duration_seconds` desde o `start_time`: só faz
    sentido para quem rodou de verdade. Faz o commit do fechamento: a
    contabilização e a publicação só valem para o que foi gravado.
    """
    # Já terminal no objeto: um desfecho nunca volta a pending/running, então
    # não há o que disputar — é o run que o despacho acabou de fechar e que
    # depois passa pela rede de segurança do `except`.
    runs = [run for run in runs if isinstance(run, str) or run.status in de]
    if not runs:
        return []
    agora = datetime.now(timezone.utc)
    valores = {"status": para, "error_message": mensagem, "error_category": categoria, "end_time": agora}

    fechados: list = []
    for run in runs:
        task_id = run if isinstance(run, str) else run.task_id
        deste = dict(valores)
        if duracao:
            deste["duration_seconds"] = _duracao(run, agora)
        condicao = [
            WorkflowRun.task_id == task_id,
            WorkflowRun.status == de[0] if len(de) == 1 else WorkflowRun.status.in_(de),
        ]
        if host is not None:
            condicao.append(WorkflowRun.host == host)
        resultado = await db.execute(
            update(WorkflowRun).where(*condicao).values(**deste)
            .execution_options(synchronize_session=False)
        )
        if resultado.rowcount:
            fechados.append((run, deste))
    await db.commit()
    if not fechados:
        return []

    objetos = await _objetos(db, fechados)
    task_ids = [run.task_id for run in objetos]
    # Uma falha na contabilização faz rollback (ver `account_terminal_run`), e o
    # rollback EXPIRA todos os objetos da sessão: o próximo run seria contado
    # com atributos expirados (e perdido), e quem chama leria `run.host` ou
    # `run.task_id` num objeto sem estado — o cancel ao host e a conclusão do
    # painel não saíam. O fechamento já está gravado: recarregar traz o mesmo
    # desfecho.
    for run in objetos:
        await _recarregar_se_expirou(db, run)
        await run_result_consumer.account_terminal_run(db, run)
    for run in objetos:
        await _recarregar_se_expirou(db, run)
    try:
        await run_events_service.publicar_conclusao(
            task_ids, status=para, mensagem=mensagem, extra=extra,
        )
    except Exception as exc:
        logger.warning(
            "Conclusão de %d run(s) fechado(s) no servidor não publicada: %s", len(objetos), exc,
        )
    return objetos


async def _recarregar_se_expirou(db: AsyncSession, run: WorkflowRun) -> None:
    estado = inspect(run)
    if estado.expired or estado.expired_attributes:
        await db.refresh(run)


async def _objetos(db: AsyncSession, fechados: list) -> list[WorkflowRun]:
    """Os runs fechados como objetos, com o que foi gravado espelhado. Quem veio
    por task_id é carregado numa consulta só."""
    por_id = [run for run, _ in fechados if isinstance(run, str)]
    carregados = {}
    if por_id:
        linhas = await db.execute(select(WorkflowRun).where(WorkflowRun.task_id.in_(por_id)))
        carregados = {r.task_id: r for r in linhas.scalars().all()}
    objetos = []
    for run, gravado in fechados:
        objeto = carregados.get(run) if isinstance(run, str) else run
        if objeto is None:
            continue
        for campo, valor in gravado.items():
            set_committed_value(objeto, campo, valor)
        objetos.append(objeto)
    return objetos


def _duracao(run, agora: datetime) -> float | None:
    inicio = getattr(run, "start_time", None)
    if inicio is None:
        return None
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    return round((agora - inicio).total_seconds(), 3)
