# tests/unit/test_observability_metricas_v2.py
"""Métricas v2 do Histórico (docs/specs/metrics-history.md §3).

O que a spec mudou de propósito e que estes testes fixam:

- taxa de sucesso = concluídas ÷ (concluídas + falhas) — em andamento e
  canceladas saem do denominador;
- percentis só de execuções concluídas com duração > 0, com a MESMA
  interpolação do `percentile_cont` do PostgreSQL no fallback em Python;
- filtros comuns (`workspace_id` → 403 fora do escopo, `workflow_id` → 404,
  `tz` → 422) e chave de cache que os inclui;
- "presa" = ativa há mais que max(3 × p50, 900 s), ou 3600 s sem p50;
- gráfico por dia com todos os dias, cortados no fuso pedido;
- campos novos do run para qualquer usuário, admin-only preservados;
- linha "Sem executor" e frota online com zeros na visão por executor.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from app.core.exceptions import WorkflowNotFoundError, WorkspaceAccessDeniedError
from app.core.executor_connections import executor_registry
from app.core.utils.estatistica import percentil_linear
from app.services import observability_service as osvc
from app.services.observability.agregados import _execucoes_presas
from app.services.observability_service import (
    ObservabilityService,
    _bloco_agora,
    _metrics_cache_key,
    _percentis,
    _resolver_escopo,
    _serialize_run,
)


# ── Dublês ───────────────────────────────────────────────────────────────────

def _user(role="admin", id_hash="usr-1"):
    u = MagicMock()
    u.role = role
    u.id_hash = id_hash
    return u


class _LinhaVazia:
    """Linha de agregação sem dados: qualquer coluna lê como None."""

    def __getattr__(self, _nome):
        return None


def _resultado(*, linha=None, linhas=None, escalar=None):
    r = MagicMock()
    r.one.return_value = linha if linha is not None else _LinhaVazia()
    r.all.return_value = list(linhas or [])
    r.scalars.return_value.all.return_value = list(linhas or [])
    r.scalar_one_or_none.return_value = escalar
    r.scalar.return_value = escalar
    return r


def _db(*respostas, dialeto="sqlite"):
    """Sessão dublê: devolve `respostas` na ordem e, esgotadas, resultados
    vazios. `dialeto` decide entre SQL do PostgreSQL e fallback em Python."""
    fila = list(respostas)

    async def _execute(stmt):
        return fila.pop(0) if fila else _resultado()

    db = MagicMock(execute=AsyncMock(side_effect=_execute))
    db.bind.dialect.name = dialeto
    return db


def _sql(db, chamada=0, dialeto=postgresql.dialect()) -> str:
    stmt = db.execute.await_args_list[chamada].args[0]
    return str(stmt.compile(dialect=dialeto, compile_kwargs={"literal_binds": False}))


@pytest.fixture(autouse=True)
def _sem_redis():
    """Presença, capacidade e ACKs vêm do Redis; aqui nada está no ar."""
    with patch.object(executor_registry, "is_online", AsyncMock(return_value=False)), \
         patch.object(executor_registry, "read_capacity", AsyncMock(return_value=None)), \
         patch.object(executor_registry, "list_pending_acks", AsyncMock(return_value=[])):
        yield


AGORA = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


# ── Percentis ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("valores, p, esperado", [
    ([], 0.5, None),
    ([42.0], 0.5, 42.0),
    ([10, 20], 0.5, 15.0),                # interpola entre vizinhos
    ([1, 2, 3, 4, 5], 0.5, 3.0),
    ([1, 2, 3, 4, 5], 0.95, 4.8),         # 0.95 * 4 = 3.8 → 4 + 0.8 * (5 - 4)
    ([5, 1, 3], 0.5, 3.0),                # não depende da ordem de entrada
])
def test_percentil_continuo_segue_o_percentile_cont_do_postgres(valores, p, esperado):
    assert percentil_linear(valores, p) == esperado


@pytest.mark.asyncio
async def test_percentis_em_python_so_olham_concluidas_com_duracao_positiva():
    """Fora do PostgreSQL a mediana é calculada em Python, mas o recorte
    (status success, duração > 0) tem de estar no SQL — senão o volume
    projetado seria a janela inteira."""
    db = _db(_resultado(linhas=[30.0, 10.0, 20.0]))

    p50, p95 = await _percentis(db, [], [0.5, 0.95])

    assert (p50, p95) == (20.0, 29.0)
    sql = _sql(db)
    assert "workflow_runs.status = " in sql
    assert "workflow_runs.duration_seconds > " in sql
    assert "percentile_cont" not in sql


@pytest.mark.asyncio
async def test_percentis_no_postgres_usam_percentile_cont_within_group():
    linha = SimpleNamespace(p0=42.0, p1=190.0)
    db = _db(_resultado(linha=linha), dialeto="postgresql")

    assert await _percentis(db, [], [0.5, 0.95]) == [42.0, 190.0]
    sql = _sql(db)
    assert "percentile_cont(" in sql
    assert "WITHIN GROUP (ORDER BY workflow_runs.duration_seconds)" in sql


# ── Filtros comuns e cache ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workspace_fora_do_escopo_e_403_para_usuario_comum():
    with pytest.raises(WorkspaceAccessDeniedError):
        await _resolver_escopo(_db(), _user("user"), ["ws-1"], workspace_id="ws-2")


@pytest.mark.asyncio
async def test_admin_filtra_qualquer_workspace_sem_consultar_o_banco():
    db = _db()
    run_f, wf_f = await _resolver_escopo(
        db, _user("admin"), [], workspace_id="ws-qualquer", como_admin=True,
    )

    assert db.execute.await_count == 0
    assert "workflow_runs.workspace_id = " in str(run_f[0])
    assert "workflows.workspace_id = " in str(wf_f[0])


@pytest.mark.asyncio
async def test_workflow_fora_do_escopo_e_404():
    """"Sem acesso" e "não existe" caem no mesmo 404: um 403 confirmaria a
    existência de workflows de outro tenant."""
    db = _db(_resultado(escalar=None))
    with pytest.raises(WorkflowNotFoundError):
        await _resolver_escopo(db, _user("user"), ["ws-1"], workflow_id="wf-x")
    assert "workflows.workspace_id IN" in _sql(db)


def test_chave_de_cache_inclui_os_filtros():
    """Sem os filtros na chave, "todos os workspaces" seria servido a quem
    pediu "só o workspace X" pelos 45 s seguintes."""
    base = _metrics_cache_key("metrics", _user("admin"), [], 30, como_admin=True)
    com_ws = _metrics_cache_key("metrics", _user("admin"), [], 30, como_admin=True, workspace_id="ws-1")
    com_wf = _metrics_cache_key(
        "metrics", _user("admin"), [], 30, como_admin=True, workspace_id="ws-1", workflow_id="wf-1",
    )

    assert len({base, com_ws, com_wf}) == 3
    assert _metrics_cache_key("metrics", _user("admin"), [], 30, como_admin=True, workspace_id=None) == base


# ── /metrics: fórmulas ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_taxa_de_sucesso_ignora_em_andamento_e_canceladas():
    principal = SimpleNamespace(
        total=17, success=8, failed=2, running=5, pending=1, cancelled=1,
        avg_duration=12.0, last_24h=3, last_7d=9, prev_7d=4, prev_7d_success=3, prev_7d_failed=1,
    )
    anterior = SimpleNamespace(total=10, success=6, failed=4)
    db = _db(
        _resultado(linha=SimpleNamespace(total=3, ativos=2)),
        _resultado(linha=principal),
        _resultado(linha=anterior),
    )

    m = await ObservabilityService.get_metrics(db, _user("admin"), [], days=7, force=True, como_admin=True)

    assert m["success_rate"] == 0.8                    # 8 / (8 + 2), não 8 / 17
    assert m["success_rate_prev_7d"] == 0.75           # 3 / (3 + 1)
    assert m["by_status"] == {
        "success": 8, "failed": 2, "running": 5, "pending": 1, "cancelled": 1, "other": 0,
    }
    assert (m["success_runs"], m["running_runs"], m["pending_runs"], m["cancelled_runs"]) == (8, 5, 1, 1)
    assert m["prev_period"] == {
        "total_runs": 10, "success_runs": 6, "failed_runs": 4, "success_rate": 0.6, "p50_seconds": None,
    }
    assert m["duration"] == {"p50_seconds": None, "p95_seconds": None}
    # Campos que a Visão geral ainda usa.
    assert (m["total_workflows"], m["active_workflows"], m["runs_last_24h"], m["runs_last_7d"], m["runs_prev_7d"]) == (3, 2, 3, 9, 4)
    assert m["avg_duration_seconds"] == 12.0


@pytest.mark.asyncio
async def test_sem_execucoes_a_taxa_e_zero_e_a_anterior_de_7d_e_nula():
    """0.0 (spec) para a taxa da janela; `null` na de 7 dias, que é o que
    esconde a seta de tendência da Visão geral em vez de mostrar "caiu para 0%"."""
    db = _db(_resultado(linha=SimpleNamespace(total=0, ativos=0)))

    m = await ObservabilityService.get_metrics(db, _user("admin"), [], days=30, force=True, como_admin=True)

    assert m["success_rate"] == 0.0
    assert m["success_rate_prev_7d"] is None
    assert m["prev_period"]["success_rate"] == 0.0
    assert m["now"]["overdue_acks"] == 0          # admin: contado
    assert m["now"]["executors"] == {"online": 0, "total": 0}
    assert m["now"]["queued_on_executors"] is None


@pytest.mark.asyncio
async def test_periodo_anterior_tem_janela_propria_de_mesmo_tamanho():
    """A comparação é com [now-2d, now-d): fica numa query própria em vez de
    alargar o WHERE principal (que os testes de janela fixam em max(days, 14))."""
    db = _db(_resultado(linha=SimpleNamespace(total=0, ativos=0)))

    await ObservabilityService.get_metrics(db, _user("admin"), [], days=30, force=True, como_admin=True)

    stmt = db.execute.await_args_list[2].args[0]
    momentos = sorted(v for v in stmt.compile().params.values() if isinstance(v, datetime))
    assert len(momentos) == 2
    assert all(m.tzinfo is not None for m in momentos)
    assert timedelta(days=29, hours=23) < momentos[1] - momentos[0] < timedelta(days=30, hours=1)
    assert timedelta(days=59) < datetime.now(timezone.utc) - momentos[0] < timedelta(days=61)


@pytest.mark.asyncio
async def test_top_falhas_traz_nome_taxa_e_ultimo_erro_resumido():
    agregado = SimpleNamespace(workflow_hash="wf-1", total_runs=20, failure_count=5)
    ultima = SimpleNamespace(
        workflow_hash="wf-1", status="failed", error_message="x" * 300,
        error_category="timeout", start_time=AGORA,
    )
    meta = SimpleNamespace(
        id_hash="wf-1", name="Integração SICAR", flag_ative=True, workspace_id="ws-1",
        owner_username="ana", workspace_name="Cadastro", origem="usuario",
    )
    db = _db(_resultado(linhas=[agregado]), _resultado(linhas=[ultima]), _resultado(linhas=[meta]))

    (item,) = await osvc._top_falhas(db, [], AGORA - timedelta(days=30))

    assert item["workflow_name"] == "Integração SICAR"
    assert item["failure_rate"] == 0.25
    assert len(item["last_error"]) == 200 and item["last_error"].endswith("…")
    assert item["last_error_category"] == "timeout"
    assert item["last_failed_at"] == AGORA.isoformat()
    # A "última falha" de cada workflow sai de UMA consulta com função de janela.
    assert "row_number() OVER (PARTITION BY workflow_runs.workflow_hash" in _sql(db, 1)


# ── Execuções presas ─────────────────────────────────────────────────────────

def _candidata(task_id, wf, minutos, host="executor:ex-2"):
    return SimpleNamespace(
        task_id=task_id, id=1, workflow_hash=wf, host=host,
        start_time=AGORA - timedelta(minutes=minutos),
    )


@pytest.mark.asyncio
async def test_presa_usa_3x_a_mediana_com_piso_de_900s_e_3600s_sem_mediana():
    candidatas = [
        _candidata("lenta-sem-p50", "wf-a", 70),   # 4200 s > 3600 (sem p50)   → presa
        _candidata("curta-sem-p50", "wf-a", 50),   # 3000 s < 3600             → não
        _candidata("piso", "wf-b", 16),            # p50 100 → max(300, 900) = 900 < 960 → presa
        _candidata("multiplo", "wf-c", 40),        # p50 1000 → 3000 > 2400    → não
        _candidata("multiplo-2", "wf-c", 60),      # 3600 > 3000               → presa
    ]
    nomes = [SimpleNamespace(id_hash="ex-2", name="geo-02")]
    db = _db(_resultado(linhas=candidatas), _resultado(), _resultado(linhas=nomes))

    with patch("app.services.observability.agregados._p50_por_workflow", AsyncMock(return_value={"wf-b": 100.0, "wf-c": 1000.0})):
        quantas, presas = await _execucoes_presas(db, [], AGORA)

    assert quantas == 3
    assert [p["run_id"] for p in presas] == ["lenta-sem-p50", "piso", "multiplo-2"]
    assert presas[0]["elapsed_seconds"] == 4200 and presas[0]["typical_seconds"] is None
    assert presas[1]["typical_seconds"] == 100.0
    assert presas[0]["executor_name"] == "geo-02"
    # A consulta já corta pelo piso: nada abaixo de 900 s pode estar preso.
    sql = _sql(db, 0)
    assert "workflow_runs.status IN" in sql and "workflow_runs.start_time <= " in sql


@pytest.mark.asyncio
async def test_presas_limita_a_cinco_mais_antigas_mas_conta_todas():
    candidatas = [_candidata(f"r{i}", "wf-a", 120 - i) for i in range(7)]
    db = _db(_resultado(linhas=candidatas))

    with patch("app.services.observability.agregados._p50_por_workflow", AsyncMock(return_value={})):
        quantas, presas = await _execucoes_presas(db, [], AGORA)

    assert quantas == 7
    assert [p["run_id"] for p in presas] == ["r0", "r1", "r2", "r3", "r4"]


# ── Bloco "agora" ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agora_conta_frota_online_fila_publicada_e_acks_so_para_admin():
    frota = [
        SimpleNamespace(id_hash="ex-1", name="a", executor_type="dedicated", is_default=False, status="active"),
        SimpleNamespace(id_hash="ex-2", name="b", executor_type="dedicated", is_default=False, status="active"),
        SimpleNamespace(id_hash="ex-3", name="c", executor_type="default", is_default=True, status="active"),
    ]
    ativos = SimpleNamespace(running=2, pending=1)
    capacidades = {"ex-1": {"running": 2, "queued": 5, "max_concurrent": 4, "max_queue": 50, "extra": 1}, "ex-2": None}
    acks = [{"job_id": "j1", "elapsed_seconds": 20.0}, {"job_id": "j2", "elapsed_seconds": 3.0}]

    with patch.object(executor_registry, "is_online", AsyncMock(side_effect=lambda eid: eid in ("ex-1", "ex-2"))), \
         patch.object(executor_registry, "read_capacity", AsyncMock(side_effect=lambda eid: capacidades.get(eid))), \
         patch.object(executor_registry, "list_pending_acks", AsyncMock(return_value=acks)):
        db = _db(_resultado(linha=ativos), _resultado(), _resultado(linhas=frota))
        admin = await _bloco_agora(db, _user("admin"), [], AGORA, como_admin=True)

        db = _db(_resultado(linha=ativos), _resultado(), _resultado(linhas=frota))
        with patch("app.services.user_executor_service.get_user_accessible_agents",
                   AsyncMock(return_value=[{"id_hash": "ex-1", "name": "a", "status": "active"},
                                           {"id_hash": "ex-9", "name": "z", "status": "inactive"}])):
            comum = await _bloco_agora(db, _user("user"), [], AGORA)

    assert (admin["running"], admin["pending"], admin["stuck_count"]) == (2, 1, 0)
    assert admin["executors"] == {"online": 2, "total": 3}
    assert admin["queued_on_executors"] == 5          # só quem publica; ex-2 online sem capacidade não zera
    assert admin["overdue_acks"] == 1                  # 20 s ≥ JOB_ACK_WARN_SECONDS; 3 s não
    # Usuário comum: frota acessível (inativos fora) e ACKs nulos.
    assert comum["executors"] == {"online": 1, "total": 1}
    assert comum["overdue_acks"] is None


# ── /runs-by-day ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_runs_por_dia_traz_todos_os_dias_cortados_no_fuso():
    """Em São Paulo (UTC-3), 01:00 UTC ainda é o dia anterior; `pending` soma
    em `running`, `cancelled` fica à parte e o resto vai para `other`."""
    hoje = datetime.now(timezone.utc)
    ontem_0100_utc = (hoje - timedelta(days=1)).replace(hour=1, minute=0, second=0, microsecond=0)
    linhas = [
        SimpleNamespace(start_time=ontem_0100_utc, status="success"),
        SimpleNamespace(start_time=hoje - timedelta(hours=2) if hoje.hour >= 5 else hoje, status="pending"),
        SimpleNamespace(start_time=hoje, status="running"),
        SimpleNamespace(start_time=hoje, status="cancelled"),
        SimpleNamespace(start_time=hoje, status="cached"),
        SimpleNamespace(start_time=hoje.replace(tzinfo=None), status="failed"),   # naive (SQLite) → UTC
    ]
    db = _db(_resultado(linhas=linhas))

    saida = await ObservabilityService.get_runs_by_day(
        db, _user("admin"), [], 7, tz="America/Sao_Paulo", como_admin=True,
    )

    dias = saida["days"]
    assert len(dias) == 7
    assert [d["day"] for d in dias] == sorted(d["day"] for d in dias)
    assert all(set(d) == {"day", "total", "success", "failed", "running", "cancelled", "other"} for d in dias)
    # O run das 01:00 UTC de ontem cai em "anteontem" no fuso de SP (−3h cruza a
    # meia-noite). Localiza o balde pela DATA no fuso pedido, não por índice fixo:
    # quando o teste roda entre 00:00–03:00 UTC, "hoje em SP" ainda é o dia
    # anterior e o `dias[-3]` escorregava um dia (falha só nessa janela).
    dia_do_sucesso = ontem_0100_utc.astimezone(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    balde = next(d for d in dias if d["day"] == dia_do_sucesso)
    assert balde["success"] == 1 and balde["total"] == 1
    assert sum(d["total"] for d in dias) == 6
    assert sum(d["running"] for d in dias) == 2
    assert sum(d["cancelled"] for d in dias) == 1
    assert sum(d["other"] for d in dias) == 1
    assert sum(d["failed"] for d in dias) == 1
    # Fallback: só (start_time, status) da janela vão para o Python.
    sql = _sql(db)
    assert "count(" not in sql and "workflow_runs.start_time >= " in sql


@pytest.mark.asyncio
async def test_runs_por_dia_no_postgres_corta_o_dia_com_at_time_zone():
    db = _db(_resultado(linhas=[SimpleNamespace(day="2026-09-06", status="success", count=2)]), dialeto="postgresql")

    with patch.object(osvc, "_agora_utc", return_value=AGORA):
        saida = await ObservabilityService.get_runs_by_day(
            db, _user("admin"), [], 3, tz="America/Sao_Paulo", como_admin=True,
        )

    sql = _sql(db)
    assert "timezone(" in sql and "GROUP BY" in sql
    assert [d["day"] for d in saida["days"]] == ["2026-09-04", "2026-09-05", "2026-09-06"]
    assert saida["days"][-1] == {
        "day": "2026-09-06", "total": 2, "success": 2, "failed": 0, "running": 0, "cancelled": 0, "other": 0,
    }


@pytest.mark.asyncio
async def test_tz_invalido_e_422_no_router(client):
    """A validação fica na borda: um nome inválido viraria erro de SQL no
    `AT TIME ZONE` (500) em vez de um 422 que a web entende."""
    from app.api.dependencies import get_db
    from app.main import app

    async def _db_falso():
        yield _db()

    app.dependency_overrides[get_db] = _db_falso
    try:
        resp = await client.get("/observability/runs-by-day", params={"days": 7, "tz": "Marte/Olimpo"})
        assert resp.status_code == 422
        resp = await client.get("/observability/metrics", params={"workspace_id": "ws-de-outro"})
        assert resp.status_code == 403
        assert resp.json()["error"] == "workspace_access_denied"
        resp = await client.get("/observability/runs", params={"tier": "xyz"})
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── /runs e /runs/{id}: serialização e filtros ───────────────────────────────

def _run_row(**over):
    base = dict(
        task_id="t-1", id=1, status="failed", start_time=AGORA, end_time=None, duration_seconds=None,
        error_message="boom", host="executor:abcdef12345", dispatch_tier="pool", workflow_hash="wf-1",
        workspace_id="ws-antigo", trigger_source="schedule", triggered_by="usr-9",
        error_category="timeout", schedule_id=7, retry_count=0, node_stats={},
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_serializacao_traz_os_campos_novos_e_reserva_os_admin_only():
    meta = {"wf-1": {
        "workflow_name": "Integração", "workflow_active": True, "owner_username": "ana",
        "workspace_id": "ws-novo", "workspace_name": "Novo", "origem": "assistente",
    }}
    kwargs = dict(
        agent_names={"abcdef12345": "geo-02"}, workflow_meta=meta,  # pragma: allowlist secret
        workspace_names={"ws-antigo": "Antigo"}, user_names={"usr-9": "bia"},
    )

    comum = _serialize_run(_run_row(), admin=False, **kwargs)
    admin = _serialize_run(_run_row(), admin=True, **kwargs)

    assert comum["executor_id"] == "abcdef12345" and comum["executor_name"] == "geo-02"
    assert comum["agent_host"] == "geo-02@12345"
    assert (comum["trigger_source"], comum["triggered_by"], comum["triggered_by_username"]) == ("schedule", "usr-9", "bia")
    assert (comum["error_category"], comum["schedule_id"]) == ("timeout", 7)
    assert comum["workflow_name"] == "Integração"
    # O workspace é o DO RUN (onde a execução aconteceu), não o atual do workflow.
    assert (comum["workspace_id"], comum["workspace_name"]) == ("ws-antigo", "Antigo")
    assert "workflow_active" not in comum and "owner_username" not in comum
    assert admin["workflow_active"] is True and admin["owner_username"] == "ana"
    # A origem do FLUXO (quem o criou) vai para QUALQUER usuário: é o selo do
    # assistente na lista, não um dado de administração.
    assert comum["workflow_origem"] == "assistente"


def test_serializacao_sem_host_e_sem_meta_devolve_nulos():
    out = _serialize_run(_run_row(host=None, triggered_by=None, workspace_id=None))
    assert out["executor_id"] is None and out["executor_name"] is None and out["agent_host"] is None
    assert out["triggered_by_username"] is None and out["workspace_name"] is None
    assert "workflow_name" not in out
    # Workflow apagado de vez: sem meta, sem origem — a tela não pinta selo.
    assert out["workflow_origem"] is None


@pytest.mark.asyncio
async def test_filtro_de_origem_do_fluxo_junta_workflows_e_nao_e_o_disparo():
    """O chip "Assistente" do Histórico recorta pelo FLUXO (`workflows.origem`),
    não pelo disparo (`workflow_runs.trigger_source`) — são eixos diferentes e
    combináveis."""
    db = _db()
    await ObservabilityService.list_runs(
        db, _user("admin"), [], workflow_origem="assistente", como_admin=True,
    )
    sql = _sql(db, 0)
    assert "JOIN workflows" in sql, "o recorte por origem precisa do join, como a busca"
    assert "workflows.origem = " in sql
    # `trigger_source` continua na projeção, mas NÃO vira recorte: o chip não
    # esconde execuções manuais de um fluxo do assistente.
    assert "workflow_runs.trigger_source = " not in sql

    # Combinado com o chip de status e com a busca, sem join duplicado.
    db = _db()
    await ObservabilityService.list_runs(
        db, _user("admin"), [], workflow_origem="assistente", status="failed", q="GDAL", como_admin=True,
    )
    sql = _sql(db, 0)
    assert sql.count("JOIN workflows") == 1
    assert "workflow_runs.status = " in sql and "workflows.name ILIKE" in sql


@pytest.mark.asyncio
async def test_lista_so_junta_workflows_quando_ha_busca():
    db = _db()
    await ObservabilityService.list_runs(
        db, _user("admin"), [], q="GDAL", tier="pool", trigger_source="schedule", como_admin=True,
    )
    com_busca = _sql(db, 0)
    assert "JOIN workflows" in com_busca
    assert "workflow_runs.error_message ILIKE" in com_busca and "workflows.name ILIKE" in com_busca
    assert "workflow_runs.dispatch_tier = " in com_busca and "workflow_runs.trigger_source = " in com_busca
    padrao = [v for v in db.execute.await_args_list[0].args[0].compile().params.values() if v == "%GDAL%"]
    assert padrao, "o termo vira %termo% nos dois ILIKE"

    db = _db()
    await ObservabilityService.list_runs(db, _user("user"), ["ws-1"], workspace_id="ws-1")
    sem_busca = _sql(db, 0)
    assert "JOIN workflows" not in sem_busca
    assert "workflow_runs.workspace_id = " in sem_busca


@pytest.mark.asyncio
async def test_busca_escapa_curingas_do_usuario():
    db = _db()
    await ObservabilityService.list_runs(db, _user("admin"), [], q="100%_a", como_admin=True)
    params = db.execute.await_args_list[0].args[0].compile().params.values()
    assert "%100\\%\\_a%" in params


@pytest.mark.asyncio
async def test_lista_resolve_nomes_em_lote_e_nao_por_linha():
    """Uma página de N runs custa a listagem + 4 SELECT ... IN (executores,
    workflows, workspaces, usuários), independentemente de N."""
    linhas = [_run_row(task_id=f"t-{i}", triggered_by=f"usr-{i}", workspace_id=f"ws-{i}") for i in range(10)]
    db = _db(_resultado(linhas=linhas))

    saida = await ObservabilityService.list_runs(db, _user("user"), ["ws-1"], limit=50)

    assert len(saida["runs"]) == 10
    assert db.execute.await_count == 5
    assert "workflow_active" not in saida["runs"][0]


@pytest.mark.asyncio
async def test_detalhe_traz_typical_seconds_do_workflow():
    run = _run_row()
    db = _db(_resultado(escalar=run))

    with patch.object(osvc, "_p50_por_workflow", AsyncMock(return_value={"wf-1": 38.5})):
        detalhe = await ObservabilityService.get_run_detail(db, "t-1", _user("user"), ["ws-antigo"])

    assert detalhe["typical_seconds"] == 38.5
    assert detalhe["trigger_source"] == "schedule"
    assert "owner_username" not in detalhe


@pytest.mark.asyncio
async def test_detalhe_de_run_ativo_nao_recomputa_a_mediana():
    """Enquanto o run CORRE (o poll frequente que o run_workflow instrui), a
    mediana de 90 dias nem faz sentido — nao computa. Mutacao: tirar o gate por
    `_STATUS_ATIVOS` faz o `_p50_por_workflow` rodar a cada poll."""
    p50 = AsyncMock(return_value={"wf-1": 38.5})
    for estado in ("running", "pending"):
        run = _run_row(status=estado, end_time=None)
        db = _db(_resultado(escalar=run))
        with patch.object(osvc, "_p50_por_workflow", p50):
            detalhe = await ObservabilityService.get_run_detail(db, "t-1", _user("user"), ["ws-antigo"])
        assert detalhe["typical_seconds"] is None, estado
    p50.assert_not_called()


# ── /metrics/executores ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_executores_incluem_sem_executor_e_frota_online_com_zeros():
    linhas = [
        SimpleNamespace(host="executor:ex-1", total_runs=4, success_runs=3, failed_runs=1, avg_duration=10.0, last_run_at=AGORA),
        SimpleNamespace(host=None, total_runs=2, success_runs=0, failed_runs=2, avg_duration=None, last_run_at=AGORA),
    ]
    frota = [
        SimpleNamespace(id_hash="ex-1", name="geo-01", executor_type="dedicated", is_default=False, status="active"),
        SimpleNamespace(id_hash="ex-2", name="geo-02", executor_type="default", is_default=True, status="active"),
        SimpleNamespace(id_hash="ex-3", name="geo-03", executor_type="dedicated", is_default=False, status="active"),
    ]
    cap = {"ex-1": {"running": 1, "queued": 2, "max_concurrent": 4, "max_queue": 50}}
    db = _db(_resultado(linhas=linhas), _resultado(), _resultado(linhas=frota))

    with patch.object(executor_registry, "is_online", AsyncMock(side_effect=lambda eid: eid in ("ex-1", "ex-2"))), \
         patch.object(executor_registry, "read_capacity", AsyncMock(side_effect=lambda eid: cap.get(eid))):
        saida = await ObservabilityService.get_executor_metrics(
            db, _user("admin"), [], days=30, force=True, como_admin=True,
        )

    por_host = {e["agent_host"]: e for e in saida["executores"]}
    assert set(por_host) == {"executor:ex-1", None, "executor:ex-2"}   # ex-3 offline e sem runs fica fora

    sem = por_host[None]
    assert sem["display_name"] == "Sem executor" and sem["unassigned"] is True
    assert (sem["executor_id"], sem["online"], sem["capacity"], sem["p50_seconds"]) == (None, False, None, None)

    ex1 = por_host["executor:ex-1"]
    assert (ex1["executor_id"], ex1["executor_type"], ex1["is_default"], ex1["status"]) == ("ex-1", "dedicated", False, "active")
    assert ex1["online"] is True and ex1["capacity"] == cap["ex-1"]
    assert ex1["success_rate"] == 0.75 and ex1["unassigned"] is False

    ex2 = por_host["executor:ex-2"]
    assert ex2["total_runs"] == 0 and ex2["online"] is True and ex2["last_run_at"] is None
    assert ex2["display_name"] == "geo-02@ex-2"


# ── /metrics/workflows ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_visao_por_workflow_lista_todos_com_zeros_e_ordena():
    inventario = [
        SimpleNamespace(id_hash="wf-b", name="Beta", flag_ative=True, workspace_id="ws-1", workspace_name="Um", origem="usuario"),
        SimpleNamespace(id_hash="wf-a", name="alfa", flag_ative=False, workspace_id="ws-1", workspace_name="Um", origem="assistente"),
        SimpleNamespace(id_hash="wf-c", name="Gama", flag_ative=True, workspace_id="ws-2", workspace_name="Dois", origem="usuario"),
    ]
    agregados = [
        SimpleNamespace(workflow_hash="wf-c", total=5, success=3, failed=1, running=1),
    ]
    # A ultima execucao concluiu; o ultimo ERRO e o da ultima falha (uma
    # consulta a parte, so para quem tem falha na janela).
    ultimas = [SimpleNamespace(workflow_hash="wf-c", status="success", error_message=None, error_category=None, start_time=AGORA)]
    ultimas_falhas = [SimpleNamespace(workflow_hash="wf-c", status="failed", error_message="Timeout", error_category="timeout", start_time=AGORA)]
    db = _db(
        _resultado(linhas=inventario), _resultado(linhas=agregados),
        _resultado(linhas=[SimpleNamespace(grupo="wf-c", duration_seconds=170.0)]),
        _resultado(linhas=ultimas), _resultado(linhas=ultimas_falhas),
    )

    saida = await ObservabilityService.get_workflows_metrics(
        db, _user("admin"), [], days=30, force=True, como_admin=True,
    )

    assert [w["workflow_hash"] for w in saida["workflows"]] == ["wf-c", "wf-a", "wf-b"]   # runs desc, nome asc (sem caixa)
    gama = saida["workflows"][0]
    assert gama["success_rate"] == 0.75 and gama["p50_seconds"] == 170.0 and gama["running_runs"] == 1
    assert (gama["last_status"], gama["last_error"], gama["last_error_category"]) == ("success", "Timeout", "timeout")
    assert gama["last_run_at"] == AGORA.isoformat()
    alfa = saida["workflows"][1]
    assert alfa["total_runs"] == 0 and alfa["active"] is False and alfa["last_run_at"] is None
    assert alfa["p50_seconds"] is None and alfa["success_rate"] == 0.0
    # Cada linha diz quem criou o fluxo: a visão "Por workflow" pinta o selo do
    # assistente e filtra por ele sem uma segunda chamada.
    assert (alfa["origem"], gama["origem"]) == ("assistente", "usuario")
    assert "workflows.deleted_at IS NULL" in _sql(db, 0)


# ══════════════════════════════════════════════════════════════════════════════
# Regressões da revisão: date_from com sufixo Z (Python 3.10) e chave de cache
# por usuário (a frota de executores não é só função dos workspaces)
# ══════════════════════════════════════════════════════════════════════════════

def test_parse_iso_aceita_o_sufixo_z_que_a_web_manda():
    from app.services.observability_service import _parse_iso
    d = _parse_iso("2026-08-07T22:05:13.123Z")
    assert d.tzinfo is not None and d.utcoffset().total_seconds() == 0
    assert _parse_iso("2026-08-07T22:05:13+00:00") == d.replace(microsecond=0)


@pytest.mark.asyncio
async def test_list_runs_aceita_date_from_em_iso_com_z():
    """`toISOString()` termina em Z; `fromisoformat` do 3.10 recusava e a tabela
    do Histórico nunca carregava em produção."""
    db = _db()
    await ObservabilityService.list_runs(
        db, _user("admin"), [], date_from="2026-08-07T22:05:13.123Z", como_admin=True,
    )
    assert "start_time >=" in _sql(db, 0)


def test_chave_de_cache_distingue_usuarios_com_os_mesmos_workspaces():
    ana = _metrics_cache_key("metrics", _user("user", "ana"), ["ws-1"], 30)
    bia = _metrics_cache_key("metrics", _user("user", "bia"), ["ws-1"], 30)
    assert ana != bia
    # A visao total tambem e chaveada pelo usuario: o mesmo admin com e sem
    # `como_admin` (REST × MCP) nao pode compartilhar a resposta cacheada.
    assert _metrics_cache_key("metrics", _user("admin", "a"), [], 30, como_admin=True) \
        != _metrics_cache_key("metrics", _user("admin", "b"), [], 30, como_admin=True)
