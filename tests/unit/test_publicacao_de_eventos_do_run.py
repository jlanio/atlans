# tests/unit/test_publicacao_de_eventos_do_run.py
"""Histórico e canal de eventos de um run: um dono só para chave, pipeline e JSON.

A escrita `rpush(history) / ltrim(-MAX) / expire(1h) / publish(canal)` existia
em quatro cópias (node_events, job_result, run inconclusivo e
`publicar_conclusao`), o JSON do `__workflow_complete__` em três, e as chaves
`workflow:{run}:history`/`:events` eram montadas à mão em seis pontos,
leitores inclusos. Uma cópia que divergisse (TTL, teto, nome da chave) não
quebrava nada na hora: o painel só deixava de ver o evento.

Os dois primeiros blocos prendem o formato de HOJE de cada caminho (passam
antes e depois da unificação); o último prova que escritores e leitores
passaram a sair do mesmo lugar — `run_events_service`.
"""
import json
from types import SimpleNamespace

import pytest

from app.api.routers.executor_ws import protocolo as P
from app.api.routers.executor_ws import resultados as RES
from app.core.constants import MAX_EVENTOS_NO_HISTORICO, REDIS_TTL_1H, WORKFLOW_COMPLETE_NODE
from app.core.executor_connections import executor_registry
from app.services import run_events_service


class _Pipe:
    def __init__(self, dono):
        self.dono = dono
        self.cmds: list[tuple] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    def rpush(self, chave, *valores):
        self.cmds.append(("rpush", chave, *valores))

    def ltrim(self, chave, inicio, fim):
        self.cmds.append(("ltrim", chave, inicio, fim))

    def expire(self, chave, ttl):
        self.cmds.append(("expire", chave, ttl))

    def publish(self, canal, valor):
        self.cmds.append(("publish", canal, valor))

    def lpush(self, chave, valor):
        self.cmds.append(("lpush", chave, valor))

    async def execute(self):
        self.dono.executados.append(self.cmds)
        return []


class _Redis:
    def __init__(self):
        self.executados: list[list[tuple]] = []
        self.soltos: list[tuple] = []

    def pipeline(self, transaction=True):
        assert transaction is False
        return _Pipe(self)

    async def setex(self, chave, ttl, valor):
        self.soltos.append(("setex", chave, ttl, valor))

    async def lpush(self, chave, valor):
        self.soltos.append(("lpush", chave, valor))

    async def expire(self, chave, ttl):
        self.soltos.append(("expire", chave, ttl))

    async def lrange(self, chave, inicio, fim):
        self.soltos.append(("lrange", chave, inicio, fim))
        return []

    def comandos(self) -> list[tuple]:
        return [cmd for bloco in self.executados for cmd in bloco] + self.soltos


# ── Formato de hoje: publicar_conclusao ──────────────────────────────────────


async def test_publicar_conclusao_nao_leva_duration_ms_e_carimba_um_instante_so(monkeypatch):
    """O servidor não mede a duração de quem ele fecha: a chave nunca saiu
    neste caminho, e todos os runs do mesmo fechamento levam o MESMO instante."""
    rc = _Redis()
    monkeypatch.setattr(run_events_service, "get_redis_pool", lambda: rc)

    await run_events_service.publicar_conclusao(
        ["r-1", "r-2"], status="failed", mensagem="Executor desconectou.",
        extra={"error_category": "transient", "retryable": True},
    )

    [bloco] = rc.executados
    eventos = [cmd[2] for cmd in bloco if cmd[0] == "publish"]
    ts = json.loads(eventos[0])["timestamp"]
    assert eventos == [
        json.dumps({
            "run_id": run_id, "node": WORKFLOW_COMPLETE_NODE, "kind": "lifecycle",
            "level": "error", "status": "failed", "timestamp": ts,
            "error": "Executor desconectou.",
            "extra": {"error_category": "transient", "retryable": True},
        })
        for run_id in ("r-1", "r-2")
    ]
    assert bloco == [
        cmd
        for run_id, ev in (("r-1", eventos[0]), ("r-2", eventos[1]))
        for cmd in (
            ("rpush", f"workflow:{run_id}:history", ev),
            ("ltrim", f"workflow:{run_id}:history", -MAX_EVENTOS_NO_HISTORICO, -1),
            ("expire", f"workflow:{run_id}:history", REDIS_TTL_1H),
            ("publish", f"workflow:{run_id}:events", ev),
        )
    ]


@pytest.mark.parametrize(("status", "level"), [("cancelled", "info"), ("success", "info"), ("failed", "error")])
async def test_publicar_conclusao_nivel_so_e_erro_na_falha(monkeypatch, status, level):
    rc = _Redis()
    monkeypatch.setattr(run_events_service, "get_redis_pool", lambda: rc)

    await run_events_service.publicar_conclusao(["r-1"], status=status, mensagem=None)

    evento = json.loads(rc.executados[0][0][2])
    assert (evento["level"], evento["status"], evento["error"], evento["extra"]) == (level, status, None, None)


# ── Formato de hoje: node_events em lote ─────────────────────────────────────


async def test_node_events_de_dois_runs_saem_num_pipeline_com_a_sequencia_de_sempre(monkeypatch):
    rc = _Redis()

    async def _dono(_executor_id, _run_id):
        return True

    monkeypatch.setattr(RES, "_run_belongs_to_agent", _dono)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._publish_node_events("ex-1", [
        {"type": "node_event", "run_id": "a", "node": "n1", "status": "started"},
        {"type": "node_event", "run_id": "b", "node": "n2", "status": "started"},
        {"type": "node_event", "run_id": "a", "node": "n1", "status": "completed"},
    ])

    a1 = json.dumps({"run_id": "a", "node": "n1", "status": "started"})
    a2 = json.dumps({"run_id": "a", "node": "n1", "status": "completed"})
    b1 = json.dumps({"run_id": "b", "node": "n2", "status": "started"})
    assert rc.executados == [[
        ("rpush", "workflow:a:history", a1, a2),
        ("ltrim", "workflow:a:history", -MAX_EVENTOS_NO_HISTORICO, -1),
        ("expire", "workflow:a:history", REDIS_TTL_1H),
        ("publish", "workflow:a:events", a1),
        ("publish", "workflow:a:events", a2),
        ("rpush", "workflow:b:history", b1),
        ("ltrim", "workflow:b:history", -MAX_EVENTOS_NO_HISTORICO, -1),
        ("expire", "workflow:b:history", REDIS_TTL_1H),
        ("publish", "workflow:b:events", b1),
    ]]


# ── Um lugar só ──────────────────────────────────────────────────────────────


def test_as_chaves_do_run_tem_um_dono():
    assert run_events_service.chave_do_historico("r-1") == "workflow:r-1:history"
    assert run_events_service.canal_do_run("r-1") == "workflow:r-1:events"


def test_anexar_eventos_grava_o_historico_com_teto_e_ttl_e_publica_cada_um():
    rc = _Redis()
    pipe = _Pipe(rc)

    run_events_service.anexar_eventos(pipe, "r-1", ["e1", "e2"])

    assert pipe.cmds == [
        ("rpush", "workflow:r-1:history", "e1", "e2"),
        ("ltrim", "workflow:r-1:history", -MAX_EVENTOS_NO_HISTORICO, -1),
        ("expire", "workflow:r-1:history", REDIS_TTL_1H),
        ("publish", "workflow:r-1:events", "e1"),
        ("publish", "workflow:r-1:events", "e2"),
    ]


def test_evento_de_conclusao_monta_as_tres_variantes_de_hoje():
    # Fechamento pelo servidor (`publicar_conclusao`): sem a chave de duração.
    assert run_events_service.evento_de_conclusao(
        "r-1", "cancelled", erro="Cancelado antes.", timestamp=10.5,
    ) == json.dumps({
        "run_id": "r-1", "node": WORKFLOW_COMPLETE_NODE, "kind": "lifecycle",
        "level": "info", "status": "cancelled", "timestamp": 10.5,
        "error": "Cancelado antes.", "extra": None,
    })
    # job_result sem início conhecido e run inconclusivo: a chave sai nula.
    assert run_events_service.evento_de_conclusao(
        "r-1", "failed", erro="x", extra={"error_category": "internal", "retryable": True},
        duration_ms=None, timestamp=1.0,
    ) == json.dumps({
        "run_id": "r-1", "node": WORKFLOW_COMPLETE_NODE, "kind": "lifecycle",
        "level": "error", "status": "failed", "timestamp": 1.0, "duration_ms": None,
        "error": "x", "extra": {"error_category": "internal", "retryable": True},
    })
    # job_result com duração medida.
    evento = json.loads(run_events_service.evento_de_conclusao("r-1", "completed", duration_ms=1234.5))
    assert list(evento) == [
        "run_id", "node", "kind", "level", "status", "timestamp", "duration_ms", "error", "extra",
    ]
    assert (evento["level"], evento["duration_ms"], evento["error"], evento["extra"]) == (
        "info", 1234.5, None, None,
    )
    assert isinstance(evento["timestamp"], float)


@pytest.fixture
def chaves_marcadas(monkeypatch):
    """Troca o dono das chaves: quem ainda monta a sua à mão aparece no teste."""
    monkeypatch.setattr(run_events_service, "chave_do_historico", lambda run_id: f"H<{run_id}>")
    monkeypatch.setattr(run_events_service, "canal_do_run", lambda run_id: f"C<{run_id}>")


def _chaves_usadas(rc: _Redis) -> set[str]:
    usadas = set()
    for cmd in rc.comandos():
        if cmd[0] in ("rpush", "ltrim", "expire", "publish", "lrange"):
            usadas.add(cmd[1])
    return usadas


async def test_todos_os_escritores_usam_as_chaves_do_dono(monkeypatch, chaves_marcadas):
    rc = _Redis()
    conn = SimpleNamespace(executor_ip=None, run_auth_cache={}, db_auth_cooldown_until=0.0)

    async def _dono(_executor_id, _run_id):
        return True

    async def _snapshot(_run_id):
        return ("executor:ex-1", "running", None)

    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)
    monkeypatch.setattr(run_events_service, "get_redis_pool", lambda: rc)
    monkeypatch.setattr(RES, "_run_belongs_to_agent", _dono)
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot)
    monkeypatch.setattr(executor_registry, "get", lambda _id: conn)
    monkeypatch.setattr(P, "_rate_state", {})

    await RES._publish_node_events("ex-1", [{"run_id": "r-ne", "node": "n1"}])
    await RES._handle_job_result("ex-1", {"job_id": "r-jr", "run_id": "r-jr", "status": "ok"})
    await RES._fechar_run_inconclusivo("ex-1", "r-inc", "teste")
    await run_events_service.publicar_conclusao(["r-pc"], status="failed", mensagem="x")

    usadas = _chaves_usadas(rc) - {"webhook_response:r-inc"}
    assert usadas == {
        f"{prefixo}<{run_id}>"
        for run_id in ("r-ne", "r-jr", "r-inc", "r-pc")
        for prefixo in ("H", "C")
    }


async def test_leitores_usam_as_chaves_do_dono(monkeypatch, chaves_marcadas):
    from app.services.observability_service import ObservabilityService

    rc = _Redis()

    class _PubSub:
        def __init__(self):
            self.canais: list[str] = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        async def subscribe(self, canal):
            self.canais.append(canal)

        async def listen(self):  # pragma: no cover - o replay já encerra
            if False:
                yield

    pubsub = _PubSub()
    sub = SimpleNamespace(pubsub=lambda: pubsub)

    async def _fechar():
        return None

    sub.aclose = _fechar

    async def _lrange_completo(chave, inicio, fim):
        rc.soltos.append(("lrange", chave, inicio, fim))
        return [json.dumps({"node": WORKFLOW_COMPLETE_NODE})]

    async def _detalhe(*_a, **_kw):
        return {"run_id": "r-obs"}

    monkeypatch.setattr(run_events_service, "new_pubsub_client", lambda: sub)
    monkeypatch.setattr(run_events_service, "get_redis_pool", lambda: SimpleNamespace(lrange=_lrange_completo))
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)
    monkeypatch.setattr(ObservabilityService, "get_run_detail", staticmethod(_detalhe))

    lotes = [lote async for lote in run_events_service.iter_run_events("r-it", timeout_s=1)]
    await ObservabilityService.get_run_events_com_detalhe(None, "r-obs", object(), ["ws-1"])

    assert lotes and lotes[-1].completo is True
    assert pubsub.canais == ["C<r-it>"]
    assert [cmd[1] for cmd in rc.soltos if cmd[0] == "lrange"] == ["H<r-it>", "H<r-obs>"]


async def test_os_tres_publicadores_da_conclusao_montam_o_evento_no_mesmo_lugar(monkeypatch):
    rc = _Redis()
    conn = SimpleNamespace(executor_ip=None, run_auth_cache={}, db_auth_cooldown_until=0.0)
    montados: list[tuple] = []
    real = run_events_service.evento_de_conclusao

    def _espiao(run_id, status, **kw):
        montados.append((run_id, status))
        return real(run_id, status, **kw)

    async def _snapshot(_run_id):
        return ("executor:ex-1", "running", None)

    monkeypatch.setattr(run_events_service, "evento_de_conclusao", _espiao)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)
    monkeypatch.setattr(run_events_service, "get_redis_pool", lambda: rc)
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot)
    monkeypatch.setattr(executor_registry, "get", lambda _id: conn)
    monkeypatch.setattr(P, "_rate_state", {})

    await RES._handle_job_result("ex-1", {"job_id": "r-jr", "run_id": "r-jr", "status": "cancelled"})
    await RES._fechar_run_inconclusivo("ex-1", "r-inc", "teste")
    await run_events_service.publicar_conclusao(["r-pc"], status="failed", mensagem="x")

    assert montados == [("r-jr", "cancelled"), ("r-inc", "failed"), ("r-pc", "failed")]
