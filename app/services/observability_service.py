# app/services/observability_service.py
# Lógica de negócio e consultas de observabilidade extraídas do router.
# Contrato com a web: docs/specs/metrics-history.md (§3).

import json
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import List, Optional

from app.core.exceptions import (
    InvalidDateFormatError,
    RunNotFoundError,
    WorkflowNotFoundError as _WfNotFound,
)
from sqlalchemy import and_, cast, Date as SaDate, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.busca import contem
from app.core.utils.estatistica import taxa_de_sucesso
from app.core.utils.logger import get_logger
from app.models.executor import Executor
from app.models.models import Workflow, WorkflowRun
from app.models.run_metrics import NodeRunMetrics
from app.models.workspace import Workspace

logger = get_logger(__name__)

# Janela padrao das agregacoes de dashboard. Sem ela, a contagem por status, a
# media de duracao e o top de falhas varriam workflow_runs INTEIRA a cada
# abertura da tela — e `avg(duration_seconds)` nao tem indice de suporte nenhum,
# entao era seq scan garantido, piorando todo mes. Com o recorte, as mesmas
# contagens passam a caber em ix_wfrun_workspace_time.
_METRICS_DEFAULT_DAYS = 90

from app.services.observability.escopo import (  # noqa: F401 — fachada p/ testes e rotas
    _agora_utc, _cache_get, _cache_set, _como_utc, _e_postgres, _iso, _metrics_cache_key, _resolver_escopo, _run_filter, _wf_filter, _zona, e_admin_global,
)
from app.services.observability.estatisticas import (  # noqa: F401 — fachada p/ testes e rotas
    _p50_por_workflow, _percentis, _percentis_por, _resumir_erro, _ultima_execucao_por_workflow,
)
from app.services.observability.frota import (  # noqa: F401 — fachada p/ testes e rotas
    _executor_id_do_host, _executores_do_escopo, _presenca,
)
from app.services.observability.runs import (  # noqa: F401 — fachada p/ testes e rotas
    _RUN_LIST_COLUMNS, _contexto_dos_runs, _resolve_workflow_meta, _serialize_run,
)
from app.services.observability.agregados import (  # noqa: F401 — fachada p/ testes e rotas
    _STATUS_ATIVOS,
    _balde_do_status, _bloco_agora, _parse_iso, _top_falhas,
)

# ── Service ───────────────────────────────────────────────────────────────────

class ObservabilityService:

    @staticmethod
    async def get_metrics(
        db: AsyncSession,
        user,
        workspace_ids: List[str],
        *,
        days: int = _METRICS_DEFAULT_DAYS,
        force: bool = False,
        workspace_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        como_admin: bool = False,
    ) -> dict:
        """Métricas agregadas do dashboard e do Histórico, todas com recorte temporal.

        `como_admin` é a visão total (sem filtro de workspace, frota inteira,
        ACKs atrasados): só a borda que confirmou o papel global a liga —
        ver `e_admin_global`.

        Eram 8 queries sequenciais, três delas SEM filtro de data nenhum
        (contagem por status, `avg(duration_seconds)` e top de falhas sobre TODO
        o histórico). Como nenhum índice cobre `duration_seconds`, a média era um
        seq scan da tabela inteira a cada abertura da tela — e piorava todo mês,
        porque `workflow_runs` não tem política de retenção.

        As agregações por status sobre `workflow_runs` cabem numa só, com
        `count(*) FILTER (WHERE ...)` por recorte. `total_runs` deixou de ser
        vitalício: é o total DA JANELA, e o `period_days` da resposta existe
        para a UI rotular isso.

        O WHERE dessa query é `max(janela pedida, 14 dias)` porque os recortes de
        7d/14d moram nos `FILTER` dela: um WHERE de 7 dias tornaria a comparação
        semana-a-semana matematicamente vazia (ver `janela_where` abaixo). O
        período anterior de mesmo tamanho (`prev_period`) fica numa query
        própria em vez de alargar esse WHERE para 2×days: com `days=90` isso
        dobraria o custo da agregação principal para servir quatro números.

        NÃO usar `asyncio.gather` aqui. Uma `AsyncSession` mapeia para UMA
        conexão asyncpg, e uma conexão não aceita statements concorrentes: o
        `gather` que existia antes prometia "8 queries em paralelo" e não
        entregava paralelismo nenhum — na melhor hipótese o driver serializava
        (ganho zero), na pior levantava InvalidRequestError sob concorrência.
        """
        run_f, wf_f = await _resolver_escopo(
            db, user, workspace_ids, workspace_id=workspace_id, workflow_id=workflow_id,
            como_admin=como_admin,
        )
        cache_key = _metrics_cache_key(
            "metrics", user, workspace_ids, days, como_admin=como_admin,
            workspace_id=workspace_id, workflow_id=workflow_id,
        )
        now       = _agora_utc()
        if not force:
            cached = await _cache_get(cache_key)
            if cached is not None:
                # As agregacoes da janela vem do cache; o bloco "now" e o
                # instante desta consulta e nunca e servido velho — e o que a
                # faixa Agora consulta a cada 30 s.
                fresco = dict(cached)
                fresco["now"] = await _bloco_agora(db, user, run_f, now, como_admin=como_admin)
                return fresco

        since     = now - timedelta(days=days)
        since_24h = now - timedelta(hours=24)
        since_7d  = now - timedelta(days=7)
        since_14d = now - timedelta(days=14)
        since_prev = now - timedelta(days=2 * days)
        prev_7d   = and_(WorkflowRun.start_time >= since_14d, WorkflowRun.start_time < since_7d)

        # O WHERE tem de cobrir o MAIOR dos dois recortes, nao o pedido. Os
        # contadores de 7d/14d sao `FILTER` DENTRO desta query: com
        # `?days=7` o WHERE `>= now-7d` interseccionado com o predicado de
        # prev_7d (`>= now-14d AND < now-7d`) da conjunto vazio, e o dashboard
        # passava a mostrar `runs_prev_7d: 0` e `success_rate_prev_7d: null`
        # para sempre — a seta de tendencia sumia em silencio. Com `days=1`,
        # pior: `runs_last_7d` valia o mesmo que `runs_last_24h`.
        janela_where = min(since, since_14d)
        # ...e os agregados que SAO da janela pedida ganham o recorte de volta
        # como FILTER, senao `total_runs` inflaria para 14 dias quando o
        # usuario pediu 7.
        na_janela = WorkflowRun.start_time >= since

        def _na_janela(status: str):
            return func.count(WorkflowRun.id).filter(na_janela, WorkflowRun.status == status)

        wf_row = (await db.execute(
            select(
                func.count(Workflow.id).label("total"),
                func.count(Workflow.id).filter(Workflow.flag_ative == True).label("ativos"),  # noqa: E712
            ).where(*wf_f)
        )).one()

        row = (await db.execute(
            select(
                func.count(WorkflowRun.id).filter(na_janela).label("total"),
                _na_janela("success").label("success"),
                _na_janela("failed").label("failed"),
                _na_janela("running").label("running"),
                _na_janela("pending").label("pending"),
                _na_janela("cancelled").label("cancelled"),
                func.avg(WorkflowRun.duration_seconds).filter(na_janela).label("avg_duration"),
                func.count(WorkflowRun.id).filter(WorkflowRun.start_time >= since_24h).label("last_24h"),
                func.count(WorkflowRun.id).filter(WorkflowRun.start_time >= since_7d).label("last_7d"),
                func.count(WorkflowRun.id).filter(prev_7d).label("prev_7d"),
                func.count(WorkflowRun.id)
                .filter(prev_7d, WorkflowRun.status == "success")
                .label("prev_7d_success"),
                func.count(WorkflowRun.id)
                .filter(prev_7d, WorkflowRun.status == "failed")
                .label("prev_7d_failed"),
            ).where(WorkflowRun.start_time >= janela_where, *run_f)
        )).one()

        # Periodo anterior de mesmo tamanho: [now-2d, now-d). E o que da
        # sentido a "1.284 execucoes" — muito ou pouco so a comparacao diz.
        no_prev = [WorkflowRun.start_time >= since_prev, WorkflowRun.start_time < since]
        prev = (await db.execute(
            select(
                func.count(WorkflowRun.id).label("total"),
                func.count(WorkflowRun.id).filter(WorkflowRun.status == "success").label("success"),
                func.count(WorkflowRun.id).filter(WorkflowRun.status == "failed").label("failed"),
            ).where(*no_prev, *run_f)
        )).one()

        p50, p95 = await _percentis(db, [na_janela, *run_f], [0.5, 0.95])
        (prev_p50,) = await _percentis(db, [*no_prev, *run_f], [0.5])

        top_failing = await _top_falhas(db, run_f, since)
        agora = await _bloco_agora(db, user, run_f, now, como_admin=como_admin)

        total_runs     = row.total or 0
        success_runs   = row.success or 0
        failed_runs    = row.failed or 0
        running_runs   = row.running or 0
        pending_runs   = row.pending or 0
        cancelled_runs = row.cancelled or 0
        runs_prev_7d   = row.prev_7d or 0
        prev_7d_ok     = row.prev_7d_success or 0
        prev_7d_falha  = row.prev_7d_failed or 0
        prev_success   = prev.success or 0
        prev_failed    = prev.failed or 0

        metrics = {
            "period_days":      days,
            "total_workflows":  wf_row.total or 0,
            "active_workflows": wf_row.ativos or 0,
            "total_runs":       total_runs,
            "by_status": {
                "success":   success_runs,
                "failed":    failed_runs,
                "running":   running_runs,
                "pending":   pending_runs,
                "cancelled": cancelled_runs,
                "other":     total_runs - success_runs - failed_runs - running_runs - pending_runs - cancelled_runs,
            },
            "success_runs":    success_runs,
            "failed_runs":     failed_runs,
            "running_runs":    running_runs,
            "pending_runs":    pending_runs,
            "cancelled_runs":  cancelled_runs,
            # Concluidas ÷ (concluidas + falhas): em andamento e canceladas
            # nao sao veredito — com elas no denominador a taxa caia em todo
            # pico de carga.
            "success_rate":    taxa_de_sucesso(success_runs, failed_runs),
            "avg_duration_seconds": round(float(row.avg_duration or 0.0), 3),
            "runs_last_24h":   row.last_24h or 0,
            "runs_last_7d":    row.last_7d or 0,
            "runs_prev_7d":    runs_prev_7d,
            # `null` (e nao 0.0) sem denominador: e o que esconde a seta de
            # tendencia na Visao geral em vez de mostrar "caiu para 0%".
            "success_rate_prev_7d": (
                taxa_de_sucesso(prev_7d_ok, prev_7d_falha) if (prev_7d_ok + prev_7d_falha) else None
            ),
            "prev_period": {
                "total_runs":   prev.total or 0,
                "success_runs": prev_success,
                "failed_runs":  prev_failed,
                "success_rate": taxa_de_sucesso(prev_success, prev_failed),
                "p50_seconds":  prev_p50,
            },
            "duration": {"p50_seconds": p50, "p95_seconds": p95},
            "now": agora,
            "top_failing_workflows": top_failing,
        }

        await _cache_set(cache_key, metrics)
        return metrics

    @staticmethod
    async def get_workflow_metrics(
        db: AsyncSession,
        workflow_hash: str,
        user,
        workspace_ids: List[str],
        limit: int = 20,
        *,
        como_admin: bool = False,
    ) -> dict:
        """Métricas detalhadas de um workflow específico.

        O resumo por nó vem de `node_run_metrics`, que já guarda o dado
        normalizado (duration_ms, status, cache_hit, features por nó). Antes
        este método baixava o JSON `node_stats` das últimas N execuções e
        reagregava tudo em Python a cada request: o tempo da página passava a
        depender do TAMANHO dos fluxos executados, e o event loop do worker
        ficava preso desserializando JSON.
        """
        wf_conditions = [
            Workflow.id_hash == workflow_hash,
            *_wf_filter(user, workspace_ids, como_admin=como_admin),
        ]

        # Só o nome é usado — `select(Workflow)` arrastava junto a `definition`
        # inteira do fluxo (dezenas de KB) para nada.
        wf_result = await db.execute(select(Workflow.name).where(*wf_conditions))
        workflow_name = wf_result.scalar_one_or_none()
        if workflow_name is None:
            raise _WfNotFound("Workflow não encontrado.")

        # Meta admin (dono + workspace) para exibir no detalhe do workflow.
        admin_meta = {}
        if como_admin:
            meta_map = await _resolve_workflow_meta(db, [workflow_hash])
            admin_meta = meta_map.get(workflow_hash) or {}

        # O acesso ao workflow (acima) não autoriza o histórico: um workflow
        # movido de workspace carregaria consigo runs produzidos no workspace
        # anterior. Os runs são filtrados pelo próprio workspace_id — ver
        # _run_filter, que reusamos para não duplicar a regra.
        runs_result = await db.execute(
            select(*_RUN_LIST_COLUMNS)
            .where(
                WorkflowRun.workflow_hash == workflow_hash,
                *_run_filter(user, workspace_ids, como_admin=como_admin),
            )
            .order_by(WorkflowRun.start_time.desc())
            .limit(limit)
        )
        runs = runs_result.all()

        if not runs:
            return {
                "workflow_id":           workflow_hash,
                "workflow_name":         workflow_name,
                "total_runs":            0,
                "failed_runs":           0,
                "success_rate":          0.0,
                "avg_duration_seconds":  0.0,
                "min_duration_seconds":  None,
                "max_duration_seconds":  None,
                "last_runs":             [],
                "node_stats_summary":    [],
                **admin_meta,
            }

        total    = len(runs)
        failed   = sum(1 for r in runs if r.status == "failed")
        success  = sum(1 for r in runs if r.status == "success")
        durations = [r.duration_seconds for r in runs if r.duration_seconds is not None]

        contexto = await _contexto_dos_runs(db, runs)
        last_runs = [_serialize_run(r, admin=como_admin, **contexto) for r in runs]

        # Resumo por nó: uma agregação em SQL sobre node_run_metrics, restrita
        # aos run_ids acima (ix_node_metrics_run cobre o IN). Runs cujo executor
        # não chegou a mandar métricas — falha antes de executar qualquer nó —
        # simplesmente não têm linha aqui, que é o mesmo que ter node_stats vazio.
        run_ids = [r.task_id for r in runs if r.task_id]
        node_stats_summary: list[dict] = []
        if run_ids:
            summary_result = await db.execute(
                select(
                    NodeRunMetrics.node_id,
                    func.max(NodeRunMetrics.node_name).label("node_name"),
                    func.count(NodeRunMetrics.id).label("execution_count"),
                    func.avg(NodeRunMetrics.duration_ms).label("avg_duration_ms"),
                    func.count(NodeRunMetrics.id)
                    .filter(NodeRunMetrics.status == "failed")
                    .label("failure_count"),
                    func.count(NodeRunMetrics.id)
                    .filter(NodeRunMetrics.cache_hit == True)  # noqa: E712
                    .label("cache_hits"),
                    func.avg(NodeRunMetrics.input_features).label("avg_input_features"),
                    func.avg(NodeRunMetrics.output_features).label("avg_output_features"),
                )
                .where(NodeRunMetrics.run_id.in_(run_ids))
                .group_by(NodeRunMetrics.node_id)
                .order_by(func.avg(NodeRunMetrics.duration_ms).desc().nullslast())
            )
            node_stats_summary = [
                {
                    "node_id":          s.node_id,
                    "node_name":        s.node_name or s.node_id,
                    "execution_count":  s.execution_count,
                    "avg_duration_ms":  round(float(s.avg_duration_ms), 2) if s.avg_duration_ms is not None else 0,
                    "failure_count":    s.failure_count,
                    "cache_hits":       s.cache_hits,
                    "avg_input_features":  round(float(s.avg_input_features)) if s.avg_input_features is not None else None,
                    "avg_output_features": round(float(s.avg_output_features)) if s.avg_output_features is not None else None,
                }
                for s in summary_result
            ]

        return {
            "workflow_id":           workflow_hash,
            "workflow_name":         workflow_name,
            "total_runs":            total,
            "failed_runs":           failed,
            # A mesma taxa das outras telas. Era `(total - failed) / total`, que
            # contava em andamento e canceladas como sucesso.
            "success_rate":          taxa_de_sucesso(success, failed),
            "avg_duration_seconds":  round(sum(durations) / len(durations), 3) if durations else 0.0,
            "min_duration_seconds":  round(min(durations), 3) if durations else None,
            "max_duration_seconds":  round(max(durations), 3) if durations else None,
            "last_runs":             last_runs,
            "node_stats_summary":    node_stats_summary,
            **admin_meta,
        }

    @staticmethod
    async def get_workflows_metrics(
        db: AsyncSession,
        user,
        workspace_ids: List[str],
        *,
        days: int = _METRICS_DEFAULT_DAYS,
        force: bool = False,
        workspace_id: Optional[str] = None,
        como_admin: bool = False,
    ) -> dict:
        """Visao "Por workflow" (spec §3.3): TODOS os workflows acessiveis, com
        zeros para os que nao rodaram na janela — a lista e um inventario, e um
        workflow ativo que nunca roda e informacao, nao ausencia.

        Quatro consultas, nenhuma por linha: o inventario (workflows +
        workspace), a agregacao por `workflow_hash` na janela, a mediana por
        workflow e a ultima execucao de cada um (funcao de janela). A "ultima"
        e a ultima DA JANELA: buscar a ultima vitalicia de cada workflow e uma
        varredura do escopo inteiro a cada abertura, e o periodo governa todos
        os blocos da tela.
        """
        run_f, wf_f = await _resolver_escopo(
            db, user, workspace_ids, workspace_id=workspace_id, como_admin=como_admin,
        )
        cache_key = _metrics_cache_key(
            "workflows", user, workspace_ids, days, como_admin=como_admin, workspace_id=workspace_id,
        )
        if not force:
            cached = await _cache_get(cache_key)
            if cached is not None:
                return cached

        now = _agora_utc()
        since = now - timedelta(days=days)
        na_janela = [WorkflowRun.start_time >= since, *run_f]

        inventario = (await db.execute(
            select(
                Workflow.id_hash,
                Workflow.name,
                Workflow.flag_ative,
                Workflow.workspace_id,
                Workflow.origem,
                Workspace.name.label("workspace_name"),
            )
            .select_from(Workflow)
            .outerjoin(Workspace, Workspace.id_hash == Workflow.workspace_id)
            .where(Workflow.deleted_at.is_(None), *wf_f)
        )).all()

        agregados = {
            row.workflow_hash: row
            for row in (await db.execute(
                select(
                    WorkflowRun.workflow_hash,
                    func.count(WorkflowRun.id).label("total"),
                    func.count(WorkflowRun.id).filter(WorkflowRun.status == "success").label("success"),
                    func.count(WorkflowRun.id).filter(WorkflowRun.status == "failed").label("failed"),
                    func.count(WorkflowRun.id).filter(WorkflowRun.status.in_(_STATUS_ATIVOS)).label("running"),
                )
                .where(*na_janela)
                .group_by(WorkflowRun.workflow_hash)
            )).all()
        }
        medianas = await _percentis_por(db, WorkflowRun.workflow_hash, na_janela, [0.5])
        com_execucao = list(agregados)
        ultimas = await _ultima_execucao_por_workflow(db, na_janela, workflow_hashes=com_execucao, com_erro=False)
        # "Ultimo erro" e o da ultima FALHA, como no top de falhas e na lista de
        # atencao — a ultima execucao pode ter concluido e o workflow ainda
        # assim ter dezenas de falhas na janela.
        com_falha = [h for h, row in agregados.items() if (row.failed or 0) > 0]
        ultimas_falhas = (
            await _ultima_execucao_por_workflow(
                db, [WorkflowRun.status == "failed", *na_janela], workflow_hashes=com_falha,
            ) if com_falha else {}
        )

        linhas = []
        for wf in inventario:
            agg = agregados.get(wf.id_hash)
            ultima = ultimas.get(wf.id_hash)
            falha = ultimas_falhas.get(wf.id_hash)
            success = (agg.success or 0) if agg else 0
            failed = (agg.failed or 0) if agg else 0
            linhas.append({
                "workflow_hash":  wf.id_hash,
                "workflow_name":  wf.name,
                "workspace_id":   wf.workspace_id,
                "workspace_name": wf.workspace_name,
                "active":         bool(wf.flag_ative),
                # Quem criou o fluxo ("usuario" | "assistente") — o selo da
                # lista. Nao confundir com `trigger_source`, que e o disparo.
                "origem":         wf.origem,
                "total_runs":     (agg.total or 0) if agg else 0,
                "success_runs":   success,
                "failed_runs":    failed,
                "running_runs":   (agg.running or 0) if agg else 0,
                "success_rate":   taxa_de_sucesso(success, failed),
                "p50_seconds":    (medianas.get(wf.id_hash) or [None])[0],
                "last_run_at":    _iso(ultima.start_time) if ultima else None,
                "last_status":    ultima.status if ultima else None,
                "last_error":     _resumir_erro(falha.error_message) if falha else None,
                "last_error_category": falha.error_category if falha else None,
            })

        linhas.sort(key=lambda linha: (-linha["total_runs"], (linha["workflow_name"] or "").casefold()))

        payload = {"period_days": days, "workflows": linhas}
        await _cache_set(cache_key, payload)
        return payload

    @staticmethod
    async def get_executor_metrics(
        db: AsyncSession,
        user,
        workspace_ids: List[str],
        *,
        days: int = _METRICS_DEFAULT_DAYS,
        force: bool = False,
        workspace_id: Optional[str] = None,
        como_admin: bool = False,
    ) -> dict:
        """Estatísticas por executor, na janela de `days` (spec §3.4).

        Eram DUAS agregações completas sobre `workflow_runs` (`GROUP BY host` e
        `GROUP BY host, status`) sem recorte de data nenhum — dois seq scans +
        hash aggregate por request, já que não havia índice em `host`. Agora é
        uma query só, com os contadores por status em `FILTER`, limitada pela
        janela (que cabe em ix_wfrun_workspace_time) e servida do mesmo cache
        curto de `get_metrics`.

        A frota entra inteira: executores online do escopo que nao rodaram
        nada na janela aparecem com zeros, senao a visao "Por executor" so
        mostraria quem trabalhou e esconderia justamente o ocioso.
        """
        run_f, _ = await _resolver_escopo(
            db, user, workspace_ids, workspace_id=workspace_id, como_admin=como_admin,
        )
        cache_key = _metrics_cache_key(
            "executores", user, workspace_ids, days, como_admin=como_admin, workspace_id=workspace_id,
        )
        if not force:
            cached = await _cache_get(cache_key)
            if cached is not None:
                return cached

        since = _agora_utc() - timedelta(days=days)
        na_janela = [WorkflowRun.start_time >= since, *run_f]

        result = await db.execute(
            select(
                WorkflowRun.host,
                func.count(WorkflowRun.id).label("total_runs"),
                func.count(WorkflowRun.id).filter(WorkflowRun.status == "success").label("success_runs"),
                func.count(WorkflowRun.id).filter(WorkflowRun.status == "failed").label("failed_runs"),
                func.avg(WorkflowRun.duration_seconds).label("avg_duration"),
                func.max(WorkflowRun.start_time).label("last_run_at"),
            )
            .where(*na_janela)
            .group_by(WorkflowRun.host)
            .order_by(func.count(WorkflowRun.id).desc())
        )
        rows = result.all()
        medianas = await _percentis_por(db, WorkflowRun.host, na_janela, [0.5])

        frota = {
            e["id_hash"]: e
            for e in await _executores_do_escopo(db, user, como_admin=como_admin)
        }
        # Hosts com execucao que nao estao na frota do escopo (executor
        # removido de um workspace, inativado, ou fora do acesso do usuario)
        # ainda precisam de nome — um SELECT IN para todos eles.
        ids_da_frota = list(frota.keys())
        ids_com_runs = [_executor_id_do_host(row.host) for row in rows if _executor_id_do_host(row.host)]
        faltantes = [i for i in ids_com_runs if i not in frota]
        if faltantes:
            extra = await db.execute(
                select(
                    Executor.id_hash, Executor.name, Executor.executor_type,
                    Executor.is_default, Executor.status,
                ).where(Executor.id_hash.in_(faltantes))
            )
            for r in extra.all():
                frota[r.id_hash] = {
                    "id_hash": r.id_hash, "name": r.name, "executor_type": r.executor_type,
                    "is_default": bool(r.is_default), "status": r.status,
                }

        # Presenca e capacidade SO da frota acessivel: quem rodou uma execucao
        # do usuario e depois saiu do escopo aparece com nome, mas o estado
        # atual dele (online, fila) nao e informacao do usuario.
        online, capacidade = await _presenca(ids_da_frota)

        def _linha(host: Optional[str], executor_id: Optional[str], row) -> dict:
            info = frota.get(executor_id) if executor_id else None
            total = (row.total_runs or 0) if row is not None else 0
            success = (row.success_runs or 0) if row is not None else 0
            failed = (row.failed_runs or 0) if row is not None else 0
            if host is None:
                display_name = "Sem executor"
            elif executor_id:
                nome = info["name"] if info else None
                display_name = f"{nome}@{executor_id[-5:]}" if nome else host
            else:
                display_name = host
            return {
                "agent_host":     host,
                "display_name":   display_name,
                "executor_id":    executor_id,
                "executor_type":  info["executor_type"] if info else None,
                "is_default":     bool(info["is_default"]) if info else False,
                "status":         info["status"] if info else None,
                "online":         bool(online.get(executor_id)) if executor_id else False,
                "capacity":       capacidade.get(executor_id) if executor_id else None,
                # Runs sem host sao falhas de despacho (nenhum executor
                # chegou a receber o job) — a tela precisa dessa distincao.
                "unassigned":     host is None,
                "total_runs":     total,
                "success_runs":   success,
                "failed_runs":    failed,
                "success_rate":   taxa_de_sucesso(success, failed),
                "avg_duration_seconds": (
                    round(float(row.avg_duration), 3) if row is not None and row.avg_duration else None
                ),
                "p50_seconds":    (medianas.get(host) or [None])[0] if host is not None else None,
                "last_run_at":    _iso(row.last_run_at) if row is not None and row.last_run_at else None,
            }

        agents_stats = [_linha(row.host or None, _executor_id_do_host(row.host), row) for row in rows]
        vistos = {row.host for row in rows if row.host}
        for eid, info in frota.items():
            host = f"executor:{eid}"
            if host not in vistos and online.get(eid):
                agents_stats.append(_linha(host, eid, None))

        agents_stats.sort(key=lambda a: (-a["total_runs"], a["display_name"].casefold()))

        payload = {"executores": agents_stats, "period_days": days}
        await _cache_set(cache_key, payload)
        return payload

    @staticmethod
    async def list_runs(
        db: AsyncSession,
        user,
        workspace_ids: List[str],
        *,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        worker_host: Optional[str] = None,
        workspace_id: Optional[str] = None,
        trigger_source: Optional[str] = None,
        tier: Optional[str] = None,
        workflow_origem: Optional[str] = None,
        q: Optional[str] = None,
        q_inclui_erro: bool = True,
        limit: int = 50,
        offset: int = 0,
        with_total: bool = False,
        como_admin: bool = False,
    ) -> dict:
        """Lista execuções paginada com filtros.

        O `COUNT(*)` completo saiu do caminho padrão: ele não usa LIMIT, cresce
        com a tabela e era pago em TODA página — inclusive no polling de runs
        ativos, que roda a cada 10s em toda tela do dashboard. Agora só é
        calculado com `with_total=True` (a UI pede na primeira página, para o
        rótulo "N execuções"); a navegação usa `has_more`, obtido pedindo
        `limit + 1` linhas e descartando a sobra.

        A busca `q` e a unica coisa que junta `workflows` a esta query (para
        casar o nome), e so quando presente: no caminho comum a listagem
        continua sendo um scan de indice em `workflow_runs` apenas.

        `workflow_origem` filtra pela origem do FLUXO ("usuario" |
        "assistente" — quem criou o workflow, nao quem disparou o run; o
        disparo e `trigger_source`). E o chip "Assistente" do Historico.
        Como `q`, precisa do join com `workflows`; runs de workflows deletados
        permanentemente ficam de fora do recorte, que e sobre fluxos vivos.

        `q_inclui_erro=False` tira `error_message` do `or_` da busca, deixando
        so o nome do workflow e o `task_id`. Existe para o chamador que NAO
        entrega a mensagem de erro como ela esta no banco: o servidor MCP so a
        publica depois de `scrub_text`, e um filtro de substring sobre a coluna
        bruta devolveria o mesmo texto por outro canal, em forma de sim/nao —
        quem chama repete a consulta estendendo o prefixo (`...:a` sem
        resultado, `...:b` sem resultado, `...:S` com um item) e recupera
        caractere a caractere justamente o que a redacao apagou. O default e
        `True` porque a REST mostra a mensagem inteira na tela: ali a busca nao
        revela nada que a propria resposta ja nao traga.
        """
        filters, _ = await _resolver_escopo(
            db, user, workspace_ids, workspace_id=workspace_id, workflow_id=workflow_id,
            como_admin=como_admin,
        )

        if status:
            filters.append(WorkflowRun.status == status)
        if worker_host:
            filters.append(WorkflowRun.host == worker_host)
        if trigger_source:
            filters.append(WorkflowRun.trigger_source == trigger_source)
        if tier:
            filters.append(WorkflowRun.dispatch_tier == tier)
        if date_from:
            try:
                filters.append(WorkflowRun.start_time >= _como_utc(_parse_iso(date_from)))
            except ValueError:
                raise InvalidDateFormatError(f"date_from inválido: {date_from}")
        if date_to:
            try:
                filters.append(WorkflowRun.start_time <= _como_utc(_parse_iso(date_to)))
            except ValueError:
                raise InvalidDateFormatError(f"date_to inválido: {date_to}")

        busca = (q or "").strip()
        if busca:
            alvos = [
                contem(Workflow.name, busca),
                # O id colado do botao "Copiar ID" do painel tambem acha a execucao.
                contem(WorkflowRun.task_id, busca),
            ]
            if q_inclui_erro:
                alvos.insert(0, contem(WorkflowRun.error_message, busca))
            filters.append(or_(*alvos))

        if workflow_origem:
            filters.append(Workflow.origem == workflow_origem)

        def _com_workflows(stmt):
            if busca or workflow_origem:
                return stmt.outerjoin(Workflow, Workflow.id_hash == WorkflowRun.workflow_hash)
            return stmt

        total = None
        if with_total:
            total_result = await db.execute(
                _com_workflows(select(func.count(WorkflowRun.id)).select_from(WorkflowRun)).where(*filters)
            )
            total = total_result.scalar() or 0

        runs_result = await db.execute(
            _com_workflows(select(*_RUN_LIST_COLUMNS))
            .where(*filters)
            .order_by(WorkflowRun.start_time.desc())
            .limit(limit + 1)
            .offset(offset)
        )
        runs = runs_result.all()
        has_more = len(runs) > limit
        runs = runs[:limit]

        contexto = await _contexto_dos_runs(db, runs)

        return {
            # `null` quando o cliente não pediu `with_total` — a UI usa
            # `has_more` para decidir se ainda há o que carregar.
            "total":    total,
            "has_more": has_more,
            "limit":  limit,
            "offset": offset,
            "runs":   [
                _serialize_run(r, include_workflow_hash=True, admin=como_admin, **contexto)
                for r in runs
            ],
        }

    @staticmethod
    async def get_run_detail(
        db: AsyncSession,
        run_id: str,
        user,
        workspace_ids: List[str],
        *,
        como_admin: bool = False,
    ) -> dict:
        """Detalhes de uma execução específica."""
        # Acesso pelo workspace DO RUN, não pelo do workflow: o workflow pode ter
        # sido movido depois desta execução, e o histórico pertence a quem tinha
        # acesso a ele quando aconteceu. A regra vem de `_run_filter`, a mesma
        # que a listagem e as métricas usam — reescrevê-la em Python aqui daria
        # duas formulações do mesmo critério. Aplicada na query, "sem acesso" e
        # "não existe" caem no mesmo 404, que é o comportamento desejado: um 403
        # confirmaria a existência do run.
        run_f = _run_filter(user, workspace_ids, como_admin=como_admin)

        run_result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.task_id == run_id, *run_f)
        )
        run = run_result.scalar_one_or_none()

        if run is None and run_id.isdigit():
            run_result = await db.execute(
                select(WorkflowRun).where(WorkflowRun.id == int(run_id), *run_f)
            )
            run = run_result.scalar_one_or_none()

        if run is None:
            raise RunNotFoundError(f"Execução '{run_id}' não encontrada.")

        contexto = await _contexto_dos_runs(db, [run])

        # A mediana de 90 dias (typical_seconds) so importa quando o run TERMINOU:
        # ela existe para o painel dizer "levou 8 min; costuma levar 40 s".
        # Enquanto o run corre, o cliente faz poll (run_workflow instrui "acompanhe
        # com get_run") e recomputar o percentil de 90 dias a cada poll era um scan
        # por chamada sem valor — a comparacao ainda nem faz sentido. So computa em
        # status terminal (nao-ATIVO).
        tipicos: dict = {}
        if run.status not in _STATUS_ATIVOS:
            tipicos = await _p50_por_workflow(db, [run.workflow_hash], _agora_utc())

        detalhe = _serialize_run(
            run, include_workflow_hash=True, include_node_stats=True,
            admin=como_admin, **contexto,
        )
        # Mediana do workflow nos ultimos 90 dias: e o que permite ao painel
        # dizer "levou 8 min; costuma levar 40 s". None enquanto o run nao termina.
        detalhe["typical_seconds"] = tipicos.get(run.workflow_hash) if isinstance(run.workflow_hash, str) else None
        return detalhe

    @staticmethod
    async def get_run_events(
        db: AsyncSession,
        run_id: str,
        user,
        workspace_ids: List[str],
        *,
        como_admin: bool = False,
    ) -> dict:
        """Eventos brutos de uma execução, na ordem em que foram publicados.

        Mesma lista que o WebSocket reproduz ao (re)conectar — aqui exposta por
        HTTP para que o painel de execução consiga abrir o log de um run que já
        terminou. Sem isto, fechar o workflow apagava o log para sempre: a store
        do frontend é volátil e a página de observabilidade só tem node_stats.

        O histórico vive no Redis com TTL de 1h; passado esse prazo devolvemos
        lista vazia com `expired=True` para o painel dizer "o log expirou" em
        vez de "não houve saída".
        """
        eventos, _ = await ObservabilityService.get_run_events_com_detalhe(
            db, run_id, user, workspace_ids, como_admin=como_admin,
        )
        return eventos

    @staticmethod
    async def get_run_events_com_detalhe(
        db: AsyncSession,
        run_id: str,
        user,
        workspace_ids: List[str],
        *,
        como_admin: bool = False,
    ) -> tuple[dict, dict]:
        """Os eventos MAIS o detalhe do run que os autorizou.

        Existe para quem precisa dos dois — hoje a tool `get_run_events` do MCP,
        que usa status e datas do run para dizer se a lista vazia é "expirou",
        "ainda rodando" ou "não houve saída". Sem isto, ela carregava o detalhe
        por fora e o serviço carregava de novo por dentro: `get_run_detail` não
        tem cache e faz de 3 a 6 consultas (entre elas um join de três tabelas e
        um percentil sobre janela de 90 dias), então eram de 6 a 12 idas ao
        banco por chamada, metade desperdício.

        Não há parâmetro para "pular a autorização" de propósito: quem chama
        recebe o detalhe que ESTE método autorizou, em vez de poder entregar um
        detalhe de outra procedência. A economia é a mesma e não abre caminho
        para um IDOR por argumento mal passado.
        """
        # Reusa a checagem de acesso do detalhe — levanta RunNotFoundError se o
        # run não existe ou não pertence ao(s) workspace(s) do usuário.
        detalhe = await ObservabilityService.get_run_detail(
            db, run_id, user, workspace_ids, como_admin=como_admin,
        )

        from app.core.redis import get_redis_pool
        from app.services.run_events_service import chave_do_historico

        # A chave sai do `task_id` CANÔNICO do run, nunca do que o chamador
        # digitou. `get_run_detail` resolve também pelo id NUMÉRICO da linha
        # (ver o ramo `run_id.isdigit()` acima), e a chave do histórico é
        # `workflow:{task_id}:history`. Usar o cru autorizava um run e lia a
        # chave de outro: `GET /observability/runs/123/events` respondia 200 com
        # `expired: true` e o log inteiro vivo sob a outra chave. Não é
        # vazamento — as chaves são escritas com uuid e um número nunca colide —,
        # é resposta silenciosamente errada, que é o pior tipo de log ausente.
        alvo = str(detalhe.get("run_id") or run_id)

        history_key = chave_do_historico(alvo)
        try:
            raw = await get_redis_pool().lrange(history_key, 0, -1)
        except Exception as exc:
            logger.warning("Falha ao ler histórico de eventos do run '%s': %s", alvo, exc)
            return {"run_id": alvo, "events": [], "expired": True}, detalhe

        events = []
        for item in raw:
            try:
                events.append(json.loads(item))
            except (TypeError, ValueError):
                continue

        return {"run_id": alvo, "events": events, "expired": not events}, detalhe

    @staticmethod
    async def get_runs_by_day(
        db: AsyncSession,
        user,
        workspace_ids: List[str],
        days: int = 7,
        *,
        workspace_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        tz: str = "UTC",
        como_admin: bool = False,
    ) -> dict:
        """Contagem de execuções por dia para o gráfico (spec §3.2).

        O dia e cortado no fuso pedido — para quem esta em Cuiaba, uma
        execucao das 22h nao pode aparecer no dia seguinte so porque em UTC ja
        era 2h. A janela comeca a meia-noite LOCAL de `days - 1` dias atras,
        para o grafico ter exatamente `days` barras de dias inteiros (a ultima
        e hoje, ate agora); e todos os dias saem, com zeros, porque um dia sem
        execucao e informacao e a barra ausente parecia um buraco no eixo.

        No PostgreSQL o corte e `start_time AT TIME ZONE tz` (a funcao
        `timezone()`), agrupado no banco. Fora dele (SQLite, nos testes e no
        harness) projeta so `(start_time, status)` da janela e agrupa em
        Python — o antigo `CAST(start_time AS DATE)` devolvia o ANO no SQLite.
        """
        zona = _zona(tz)
        run_f, _ = await _resolver_escopo(
            db, user, workspace_ids, workspace_id=workspace_id, workflow_id=workflow_id,
            como_admin=como_admin,
        )

        now = _agora_utc()
        hoje = now.astimezone(zona).date()
        primeiro_dia = hoje - timedelta(days=days - 1)
        since = datetime.combine(primeiro_dia, dt_time.min, tzinfo=zona).astimezone(timezone.utc)
        base_filter = [WorkflowRun.start_time >= since, *run_f]

        dias = {
            (primeiro_dia + timedelta(days=i)).isoformat(): {
                "day": (primeiro_dia + timedelta(days=i)).isoformat(),
                "total": 0, "success": 0, "failed": 0, "running": 0, "cancelled": 0, "other": 0,
            }
            for i in range(days)
        }

        if _e_postgres(db):
            dia_local = cast(func.timezone(tz, WorkflowRun.start_time), SaDate)
            result = await db.execute(
                select(dia_local.label("day"), WorkflowRun.status, func.count(WorkflowRun.id).label("count"))
                .where(*base_filter)
                .group_by(dia_local, WorkflowRun.status)
            )
            contagens = [(str(row.day), row.status, row.count or 0) for row in result.all()]
        else:
            result = await db.execute(
                select(WorkflowRun.start_time, WorkflowRun.status).where(*base_filter)
            )
            contagens = [
                (_como_utc(row.start_time).astimezone(zona).date().isoformat(), row.status, 1)
                for row in result.all()
                if row.start_time is not None
            ]

        for dia, status, n in contagens:
            balde = dias.get(dia)
            if balde is None:
                continue
            balde["total"] += n
            balde[_balde_do_status(status)] += n

        return {"days": list(dias.values())}


