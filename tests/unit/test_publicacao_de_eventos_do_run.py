# tests/unit/test_publicacao_de_eventos_do_run.py
"""History and event channel of a run: a single owner for key, pipeline and JSON.

The write `rpush(history) / ltrim(-MAX) / expire(1h) / publish(canal)` existed
in four copies (node_events, job_result, inconclusive run and
`publicar_conclusao`), the `__workflow_complete__` JSON in three, and the keys
`workflow:{run}:history`/`:events` were built by hand in six places, readers
included. A copy that diverged (TTL, ceiling, key name) broke nothing right
away: the dashboard just stopped seeing the event.

The first two blocks pin down TODAY's format of each path (they pass before and
after the unification); the last one proves that writers and readers now come
from the same place — `run_events_service`.
"""
import json
from types import SimpleNamespace

import pytest

from app.api.routers.executor_ws import protocolo as P
from app.api.routers.executor_ws import resultados as RES
from app.core.constants import MAX_EVENTS_IN_HISTORY, REDIS_TTL_1H, WORKFLOW_COMPLETE_NODE
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


# ── Today's format: publicar_conclusao ───────────────────────────────────────


async def test_publish_completion_omits_duration_ms_and_stamps_a_single_instant(monkeypatch):
    """The server does not measure the duration of what it closes: the key never
    went out on this path, and all runs of the same closing carry the SAME instant."""
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
            ("ltrim", f"workflow:{run_id}:history", -MAX_EVENTS_IN_HISTORY, -1),
            ("expire", f"workflow:{run_id}:history", REDIS_TTL_1H),
            ("publish", f"workflow:{run_id}:events", ev),
        )
    ]


@pytest.mark.parametrize(("status", "level"), [("cancelled", "info"), ("success", "info"), ("failed", "error")])
async def test_publish_completion_level_is_error_only_on_failure(monkeypatch, status, level):
    rc = _Redis()
    monkeypatch.setattr(run_events_service, "get_redis_pool", lambda: rc)

    await run_events_service.publicar_conclusao(["r-1"], status=status, mensagem=None)

    evento = json.loads(rc.executados[0][0][2])
    assert (evento["level"], evento["status"], evento["error"], evento["extra"]) == (level, status, None, None)


# ── Today's format: batched node_events ──────────────────────────────────────


async def test_node_events_of_two_runs_go_out_in_one_pipeline_with_the_usual_sequence(monkeypatch):
    rc = _Redis()

    async def _owner(_executor_id, _run_id):
        return True

    monkeypatch.setattr(RES, "_run_belongs_to_agent", _owner)
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
        ("ltrim", "workflow:a:history", -MAX_EVENTS_IN_HISTORY, -1),
        ("expire", "workflow:a:history", REDIS_TTL_1H),
        ("publish", "workflow:a:events", a1),
        ("publish", "workflow:a:events", a2),
        ("rpush", "workflow:b:history", b1),
        ("ltrim", "workflow:b:history", -MAX_EVENTS_IN_HISTORY, -1),
        ("expire", "workflow:b:history", REDIS_TTL_1H),
        ("publish", "workflow:b:events", b1),
    ]]


# ── A single place ───────────────────────────────────────────────────────────


def test_the_run_keys_have_an_owner():
    assert run_events_service.chave_do_historico("r-1") == "workflow:r-1:history"
    assert run_events_service.canal_do_run("r-1") == "workflow:r-1:events"


def test_append_events_writes_history_with_ceiling_and_ttl_and_publishes_each():
    rc = _Redis()
    pipe = _Pipe(rc)

    run_events_service.append_events(pipe, "r-1", ["e1", "e2"])

    assert pipe.cmds == [
        ("rpush", "workflow:r-1:history", "e1", "e2"),
        ("ltrim", "workflow:r-1:history", -MAX_EVENTS_IN_HISTORY, -1),
        ("expire", "workflow:r-1:history", REDIS_TTL_1H),
        ("publish", "workflow:r-1:events", "e1"),
        ("publish", "workflow:r-1:events", "e2"),
    ]


def test_completion_event_builds_the_three_current_variants():
    # Closing by the server (`publicar_conclusao`): without the duration key.
    assert run_events_service.evento_de_conclusao(
        "r-1", "cancelled", erro="Cancelado antes.", timestamp=10.5,
    ) == json.dumps({
        "run_id": "r-1", "node": WORKFLOW_COMPLETE_NODE, "kind": "lifecycle",
        "level": "info", "status": "cancelled", "timestamp": 10.5,
        "error": "Cancelado antes.", "extra": None,
    })
    # job_result with no known start and inconclusive run: the key goes out null.
    assert run_events_service.evento_de_conclusao(
        "r-1", "failed", erro="x", extra={"error_category": "internal", "retryable": True},
        duration_ms=None, timestamp=1.0,
    ) == json.dumps({
        "run_id": "r-1", "node": WORKFLOW_COMPLETE_NODE, "kind": "lifecycle",
        "level": "error", "status": "failed", "timestamp": 1.0, "duration_ms": None,
        "error": "x", "extra": {"error_category": "internal", "retryable": True},
    })
    # job_result with a measured duration.
    evento = json.loads(run_events_service.evento_de_conclusao("r-1", "completed", duration_ms=1234.5))
    assert list(evento) == [
        "run_id", "node", "kind", "level", "status", "timestamp", "duration_ms", "error", "extra",
    ]
    assert (evento["level"], evento["duration_ms"], evento["error"], evento["extra"]) == (
        "info", 1234.5, None, None,
    )
    assert isinstance(evento["timestamp"], float)


@pytest.fixture
def marked_keys(monkeypatch):
    """Swaps the owner of the keys: whoever still builds their own by hand shows up in the test."""
    monkeypatch.setattr(run_events_service, "chave_do_historico", lambda run_id: f"H<{run_id}>")
    monkeypatch.setattr(run_events_service, "canal_do_run", lambda run_id: f"C<{run_id}>")


def _used_keys(rc: _Redis) -> set[str]:
    usadas = set()
    for cmd in rc.comandos():
        if cmd[0] in ("rpush", "ltrim", "expire", "publish", "lrange"):
            usadas.add(cmd[1])
    return usadas


async def test_all_writers_use_the_owner_keys(monkeypatch, marked_keys):
    rc = _Redis()
    conn = SimpleNamespace(executor_ip=None, run_auth_cache={}, db_auth_cooldown_until=0.0)

    async def _owner(_executor_id, _run_id):
        return True

    async def _snapshot(_run_id):
        return ("executor:ex-1", "running", None)

    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)
    monkeypatch.setattr(run_events_service, "get_redis_pool", lambda: rc)
    monkeypatch.setattr(RES, "_run_belongs_to_agent", _owner)
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot)
    monkeypatch.setattr(executor_registry, "get", lambda _id: conn)
    monkeypatch.setattr(P, "_rate_state", {})

    await RES._publish_node_events("ex-1", [{"run_id": "r-ne", "node": "n1"}])
    await RES._handle_job_result("ex-1", {"job_id": "r-jr", "run_id": "r-jr", "status": "ok"})
    await RES._close_inconclusive_run("ex-1", "r-inc", "teste")
    await run_events_service.publicar_conclusao(["r-pc"], status="failed", mensagem="x")

    usadas = _used_keys(rc) - {"webhook_response:r-inc"}
    assert usadas == {
        f"{prefixo}<{run_id}>"
        for run_id in ("r-ne", "r-jr", "r-inc", "r-pc")
        for prefixo in ("H", "C")
    }


async def test_readers_use_the_owner_keys(monkeypatch, marked_keys):
    from app.services.observability_service import ObservabilityService

    rc = _Redis()

    class _PubSub:
        def __init__(self):
            self.channels: list[str] = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        async def subscribe(self, canal):
            self.channels.append(canal)

        async def listen(self):  # pragma: no cover - the replay already ends it
            if False:
                yield

    pubsub = _PubSub()
    sub = SimpleNamespace(pubsub=lambda: pubsub)

    async def _close():
        return None

    sub.aclose = _close

    async def _lrange_complete(chave, inicio, fim):
        rc.soltos.append(("lrange", chave, inicio, fim))
        return [json.dumps({"node": WORKFLOW_COMPLETE_NODE})]

    async def _detail(*_a, **_kw):
        return {"run_id": "r-obs"}

    monkeypatch.setattr(run_events_service, "new_pubsub_client", lambda: sub)
    monkeypatch.setattr(run_events_service, "get_redis_pool", lambda: SimpleNamespace(lrange=_lrange_complete))
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)
    monkeypatch.setattr(ObservabilityService, "get_run_detail", staticmethod(_detail))

    lotes = [lote async for lote in run_events_service.iter_run_events("r-it", timeout_s=1)]
    await ObservabilityService.get_run_events_with_detail(None, "r-obs", object(), ["ws-1"])

    assert lotes and lotes[-1].completo is True
    assert pubsub.channels == ["C<r-it>"]
    assert [cmd[1] for cmd in rc.soltos if cmd[0] == "lrange"] == ["H<r-it>", "H<r-obs>"]


async def test_the_three_completion_publishers_build_the_event_in_the_same_place(monkeypatch):
    rc = _Redis()
    conn = SimpleNamespace(executor_ip=None, run_auth_cache={}, db_auth_cooldown_until=0.0)
    montados: list[tuple] = []
    real = run_events_service.evento_de_conclusao

    def _spy(run_id, status, **kw):
        montados.append((run_id, status))
        return real(run_id, status, **kw)

    async def _snapshot(_run_id):
        return ("executor:ex-1", "running", None)

    monkeypatch.setattr(run_events_service, "evento_de_conclusao", _spy)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)
    monkeypatch.setattr(run_events_service, "get_redis_pool", lambda: rc)
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot)
    monkeypatch.setattr(executor_registry, "get", lambda _id: conn)
    monkeypatch.setattr(P, "_rate_state", {})

    await RES._handle_job_result("ex-1", {"job_id": "r-jr", "run_id": "r-jr", "status": "cancelled"})
    await RES._close_inconclusive_run("ex-1", "r-inc", "teste")
    await run_events_service.publicar_conclusao(["r-pc"], status="failed", mensagem="x")

    assert montados == [("r-jr", "cancelled"), ("r-inc", "failed"), ("r-pc", "failed")]
