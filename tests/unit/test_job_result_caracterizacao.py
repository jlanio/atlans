# tests/unit/test_job_result_caracterizacao.py
"""Caracterização do `_handle_job_result`: o que ele grava, publica e em que ordem.

O handler recebe resultado de executores ANTIGOS e NOVOS em campo, então o
formato e a ordem de cada efeito são contrato — com o consumer de `run_results`,
com o webhook síncrono (BRPOP em `webhook_response:{run}`) e com o painel (o
`__workflow_complete__`). Um Redis que anota cada comando na ordem em que chega
prende:

- a ordem banco → Redis → webhook: leitura do run, chave efêmera do resultado,
  fila `run_results`, `webhook_response`, Artifact do body no MinIO e, por
  último, histórico + canal do `__workflow_complete__`;
- o formato exato (chaves, ordem, valores) de cada payload nos desfechos ok,
  falha com e sem taxonomia e cancelado — do executor antigo (sem `run_id`, sem
  `error_category`) e do novo;
- a validação e a truncagem de `stats`/`error` na entrada, e o erro explícito
  ao webhook quando a truncagem levou até as chaves de controle;
- a idempotência (job_result repetido de run terminal), a recusa por memo, o
  rate limit e o fechamento do run como falho quando o resultado se perde;
- que a falha de um destino não impede os seguintes.
"""
import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.api.routers.executor_ws import protocolo as P
from app.api.routers.executor_ws import resultados as RES
from app.core.constants import MAX_EVENTOS_NO_HISTORICO, REDIS_TTL_1H, WORKFLOW_COMPLETE_NODE
from app.core.executor_connections import executor_registry
from flow.utils.protocolo_ws import (
    STATS_CONTROLE_DESCARTADO,
    STATS_TAMANHO_ORIGINAL,
    STATS_TRUNCADO,
)

EX = "ex-1"
RUN = "run-1"
IP = "203.0.113.7"
HIST = f"workflow:{RUN}:history"
CANAL = f"workflow:{RUN}:events"
WEBHOOK = f"webhook_response:{RUN}"


# ── Dublês ────────────────────────────────────────────────────────────────────


class _Pipe:
    """Pipeline que só chega ao diário no `execute` — tudo ou nada, como no Redis."""

    def __init__(self, rc):
        self._rc = rc
        self._cmds: list[tuple] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    def rpush(self, chave, *valores):
        self._cmds.append(("pipe.rpush", chave, *valores))

    def ltrim(self, chave, inicio, fim):
        self._cmds.append(("pipe.ltrim", chave, inicio, fim))

    def expire(self, chave, ttl):
        self._cmds.append(("pipe.expire", chave, ttl))

    def publish(self, canal, valor):
        self._cmds.append(("pipe.publish", canal, valor))

    def lpush(self, chave, valor):
        self._cmds.append(("pipe.lpush", chave, valor))

    async def execute(self):
        self._rc.anota(*self._cmds, ("pipe.execute",))
        return []


class _Redis:
    """Anota, em ordem, cada comando que chega. `falhar(cmd)` decide quais levantam."""

    def __init__(self, diario: list, falhar):
        self._diario = diario
        self._falhar = falhar

    def anota(self, *cmds):
        for cmd in cmds:
            if self._falhar(cmd):
                raise ConnectionError(f"redis recusou {cmd[0]}")
        self._diario.extend(cmds)

    async def setex(self, chave, ttl, valor):
        self.anota(("setex", chave, ttl, valor))

    async def lpush(self, chave, valor):
        self.anota(("lpush", chave, valor))

    async def expire(self, chave, ttl):
        self.anota(("expire", chave, ttl))

    def pipeline(self, transaction=True):
        assert transaction is False
        return _Pipe(self)


@pytest.fixture
def cenario(monkeypatch):
    """Executor conectado a ESTE worker, run 'running' dele, Redis anotando tudo.

    `linha` é o que `_query_run_snapshot` devolve (host, status, start_time);
    `falhar` recebe cada comando do Redis e diz se ele levanta.
    """
    diario: list[tuple] = []
    estado = SimpleNamespace(
        diario=diario,
        conn=SimpleNamespace(executor_ip=IP, run_auth_cache={}, db_auth_cooldown_until=0.0),
        linha=(f"executor:{EX}", "running", datetime.now(timezone.utc) - timedelta(seconds=10)),
        falhar=lambda _cmd: False,
        body_falha=None,
    )

    async def _snapshot(run_id):
        diario.append(("snapshot", run_id))
        if isinstance(estado.linha, Exception):
            raise estado.linha
        return estado.linha

    async def _body(run_id, executor_id, body_ref):
        diario.append(("body_artifact", run_id, executor_id, body_ref))
        if estado.body_falha is not None:
            raise estado.body_falha

    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot)
    monkeypatch.setattr(RES, "_JOB_RESULT_DB_RETRY_DELAY", 0.0)
    monkeypatch.setattr(RES, "_register_webhook_response_artifact", _body)
    monkeypatch.setattr(executor_registry, "get", lambda _id: estado.conn)
    monkeypatch.setattr(
        "app.core.redis.get_redis_pool", lambda: _Redis(diario, lambda cmd: estado.falhar(cmd)),
    )
    # O logger do app só propaga ao root quando o root já tinha handler no
    # import; aqui a propagação é garantida para o caplog enxergar as mensagens.
    monkeypatch.setattr(RES.logger, "propagate", True)
    return estado


def _nomes(diario) -> list[str]:
    return [cmd[0] for cmd in diario]


def _unico(diario, nome, chave):
    achados = [cmd for cmd in diario if cmd[0] == nome and cmd[1] == chave]
    assert len(achados) == 1, f"{nome} {chave}: {achados}"
    return achados[0]


def _run_result(diario) -> tuple[str, dict]:
    raw = _unico(diario, "lpush", "run_results")[2]
    return raw, json.loads(raw)


def _conclusao(diario) -> tuple[str, dict]:
    raw = _unico(diario, "pipe.publish", CANAL)[2]
    return raw, json.loads(raw)


def _run_result_esperado(
    obtido: dict, *, status, error_message=None, error_category=None, retryable=False,
    executor_ip=IP, stats_json="{}",
) -> str:
    """O envelope da fila, byte a byte: cabeçalho do `json.dumps` + `stats` emendado.

    `end_time` e `duration_seconds` dependem do relógio e vêm do obtido; o resto
    é o que o contrato fixa.
    """
    head = json.dumps({
        "task_id":          RUN,
        "status":           status,
        "error_message":    error_message,
        "error_category":   error_category,
        "retryable":        retryable,
        "end_time":         obtido["end_time"],
        "duration_seconds": obtido["duration_seconds"],
        "executor_ip":      executor_ip,
    })
    return f'{head[:-1]},"stats":{stats_json}}}'


def _conclusao_esperada(obtido: dict, *, level, status, error=None, extra=None) -> str:
    return json.dumps({
        "run_id":      RUN,
        "node":        WORKFLOW_COMPLETE_NODE,
        "kind":        "lifecycle",
        "level":       level,
        "status":      status,
        "timestamp":   obtido["timestamp"],
        "duration_ms": obtido["duration_ms"],
        "error":       error,
        "extra":       extra,
    })


def _pipeline_da_conclusao(raw: str) -> list[tuple]:
    return [
        ("pipe.rpush", HIST, raw),
        ("pipe.ltrim", HIST, -MAX_EVENTOS_NO_HISTORICO, -1),
        ("pipe.expire", HIST, REDIS_TTL_1H),
        ("pipe.publish", CANAL, raw),
        ("pipe.execute",),
    ]


def _efemero(**campos) -> str:
    base = {
        "job_id": RUN, "status": None, "run_id": None, "error": None,
        "error_category": None, "retryable": False,
    }
    base.update(campos)
    return json.dumps(base)


def _mensagens(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == RES.logger.name]


# ── Desfechos: formato e ordem ────────────────────────────────────────────────


async def test_ok_do_executor_novo_grava_na_ordem_e_no_formato_de_sempre(cenario, caplog):
    stats = {"n1": {"status": "completed", "rows": 3}, "__metrics__": {"run": {"duration_ms": 10}}}
    # Posse já provada por node_events: o memo não dispensa a leitura e sai no fim.
    cenario.conn.run_auth_cache[RUN] = (True, time.monotonic() + 60)

    with caplog.at_level("INFO"):
        await RES._handle_job_result(EX, {
            "type": "job_result", "job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats,
        })

    d = cenario.diario
    assert _nomes(d) == [
        "snapshot", "setex", "lpush",
        "pipe.rpush", "pipe.ltrim", "pipe.expire", "pipe.publish", "pipe.execute",
    ]
    assert d[0] == ("snapshot", RUN)
    assert d[1] == ("setex", f"executor:{EX}:results:{RUN}", 300, _efemero(status="ok", run_id=RUN))

    raw, res = _run_result(d)
    assert raw == _run_result_esperado(res, status="success", stats_json=json.dumps(stats))
    assert 10 <= res["duration_seconds"] < 11
    fim = datetime.fromisoformat(res["end_time"])
    assert fim.utcoffset() == timedelta(0)
    assert abs((datetime.now(timezone.utc) - fim).total_seconds()) < 5

    raw_ev, ev = _conclusao(d)
    assert raw_ev == _conclusao_esperada(ev, level="info", status="completed")
    assert abs(ev["duration_ms"] - res["duration_seconds"] * 1000) < 1
    assert abs(ev["timestamp"] - time.time()) < 5
    assert d[3:] == _pipeline_da_conclusao(raw_ev)

    assert RUN not in cenario.conn.run_auth_cache
    assert "Resultado do job 'run-1' recebido do executor 'ex-1': status=ok." in _mensagens(caplog)


async def test_falha_do_executor_antigo_sem_run_id_nem_taxonomia(cenario, caplog):
    """O formato do back-pressure/shutdown: só `job_id`, `status` e `error`."""
    erro = "Fila do executor cheia — back-pressure."
    cenario.linha = (f"executor:{EX}", "running", None)

    with caplog.at_level("INFO"):
        await RES._handle_job_result(EX, {
            "type": "job_result", "job_id": RUN, "status": "error", "error": erro,
        })

    d = cenario.diario
    assert _nomes(d) == [
        "snapshot", "setex", "lpush", "lpush", "expire",
        "pipe.rpush", "pipe.ltrim", "pipe.expire", "pipe.publish", "pipe.execute",
    ]
    assert d[1][3] == _efemero(status="error", run_id=None, error=erro)

    raw, res = _run_result(d)
    assert raw == _run_result_esperado(res, status="failed", error_message=erro)
    assert res["duration_seconds"] is None

    assert d[3] == ("lpush", WEBHOOK, json.dumps({"job_status": "error", "error": erro, "response": None}))
    assert d[4] == ("expire", WEBHOOK, 300)

    raw_ev, ev = _conclusao(d)
    assert raw_ev == _conclusao_esperada(
        ev, level="error", status="failed", error=erro,
        extra={"error_category": None, "retryable": False},
    )
    assert ev["duration_ms"] is None
    assert d[5:] == _pipeline_da_conclusao(raw_ev)
    assert (
        "Resultado do job 'run-1' recebido do executor 'ex-1': status=error "
        "category=internal retryable=False."
    ) in _mensagens(caplog)


async def test_falha_do_executor_novo_leva_a_taxonomia(cenario, caplog):
    with caplog.at_level("INFO"):
        await RES._handle_job_result(EX, {
            "type": "job_result", "job_id": RUN, "run_id": RUN, "status": "error",
            "error": "coluna 'x' não existe", "error_category": "user", "retryable": True,
            "stats": {"n1": {"status": "failed"}},
        })

    d = cenario.diario
    assert d[1][3] == _efemero(
        status="error", run_id=RUN, error="coluna 'x' não existe",
        error_category="user", retryable=True,
    )
    raw, res = _run_result(d)
    assert raw == _run_result_esperado(
        res, status="failed", error_message="coluna 'x' não existe",
        error_category="user", retryable=True,
        stats_json=json.dumps({"n1": {"status": "failed"}}),
    )
    raw_ev, ev = _conclusao(d)
    assert raw_ev == _conclusao_esperada(
        ev, level="error", status="failed", error="coluna 'x' não existe",
        extra={"error_category": "user", "retryable": True},
    )
    assert (
        "Resultado do job 'run-1' recebido do executor 'ex-1': status=error "
        "category=user retryable=True."
    ) in _mensagens(caplog)


async def test_cancelado_nao_e_falha_nem_leva_taxonomia(cenario):
    """Cancelar é pedido do usuário: nível info, sem categoria, sem retryable."""
    erro = "Cancelado pelo usuário."
    await RES._handle_job_result(EX, {
        "type": "job_result", "job_id": RUN, "run_id": RUN, "status": "cancelled",
        "error": erro, "error_category": "user", "retryable": True,
    })

    d = cenario.diario
    assert d[1][3] == _efemero(status="cancelled", run_id=RUN, error=erro)
    raw, res = _run_result(d)
    assert raw == _run_result_esperado(res, status="cancelled", error_message=erro)
    # O webhook síncrono é destravado com o status cru do executor.
    assert _unico(d, "lpush", WEBHOOK)[2] == json.dumps(
        {"job_status": "cancelled", "error": erro, "response": None},
    )
    raw_ev, ev = _conclusao(d)
    assert raw_ev == _conclusao_esperada(ev, level="info", status="cancelled", error=erro)


async def test_start_time_naive_e_lido_como_utc(cenario):
    inicio = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=30)
    cenario.linha = (f"executor:{EX}", "running", inicio)

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})

    _, res = _run_result(cenario.diario)
    assert 30 <= res["duration_seconds"] < 31
    _, ev = _conclusao(cenario.diario)
    assert 30_000 <= ev["duration_ms"] < 31_000


async def test_ip_da_conexao_passado_explicitamente_vence_o_registro(cenario):
    await RES._handle_job_result(
        EX, {"job_id": RUN, "run_id": RUN, "status": "ok"}, executor_ip="198.51.100.9",
    )
    _, res = _run_result(cenario.diario)
    assert res["executor_ip"] == "198.51.100.9"


async def test_sem_conexao_neste_worker_o_ip_vai_nulo(cenario):
    cenario.conn = None
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})
    raw, res = _run_result(cenario.diario)
    assert raw == _run_result_esperado(res, status="success", executor_ip=None)


# ── Webhook síncrono e body no MinIO ─────────────────────────────────────────


async def test_response_inline_vai_ao_webhook_antes_da_conclusao(cenario):
    resposta = {"status": 201, "headers": {"X-Id": "7"}, "body": {"id": 7}}
    stats = {"n1": {"status": "completed"}, "__response__": resposta}

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    d = cenario.diario
    assert _nomes(d) == [
        "snapshot", "setex", "lpush", "lpush", "expire",
        "pipe.rpush", "pipe.ltrim", "pipe.expire", "pipe.publish", "pipe.execute",
    ]
    assert d[2][1] == "run_results"
    assert d[3] == ("lpush", WEBHOOK, json.dumps({"job_status": "ok", "error": None, "response": resposta}))
    assert d[4] == ("expire", WEBHOOK, 300)


async def test_ok_sem_response_node_nao_toca_no_webhook(cenario):
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": {"n1": {}}})
    assert not [cmd for cmd in cenario.diario if WEBHOOK in cmd]


async def test_body_no_minio_registra_o_artifact_entre_o_webhook_e_a_conclusao(cenario):
    body_ref = {"s3_key": f"webhook-responses/ws-1/{RUN}/body.json", "size": 2048}
    resposta = {"status": 200, "body_ref": body_ref}

    await RES._handle_job_result(EX, {
        "job_id": RUN, "run_id": RUN, "status": "ok", "stats": {"__response__": resposta},
    })

    d = cenario.diario
    assert _nomes(d) == [
        "snapshot", "setex", "lpush", "lpush", "expire", "body_artifact",
        "pipe.rpush", "pipe.ltrim", "pipe.expire", "pipe.publish", "pipe.execute",
    ]
    assert d[5] == ("body_artifact", RUN, EX, body_ref)


async def test_body_ref_sem_s3_key_nao_registra_artifact(cenario):
    await RES._handle_job_result(EX, {
        "job_id": RUN, "run_id": RUN, "status": "ok",
        "stats": {"__response__": {"status": 200, "body_ref": {"size": 1}}},
    })
    assert "body_artifact" not in _nomes(cenario.diario)


@pytest.mark.parametrize("body_ref", ["webhook-responses/ws-1/body.json", ["s3_key"], 7])
async def test_body_ref_fora_do_formato_nao_impede_a_conclusao(cenario, body_ref):
    """Um executor defeituoso (ou comprometido) que manda o `body_ref` fora do
    formato não tira do painel o fim do run: o body não é registrado, e a
    conclusão sai como sempre."""
    await RES._handle_job_result(EX, {
        "job_id": RUN, "run_id": RUN, "status": "ok",
        "stats": {"__response__": {"status": 200, "body_ref": body_ref}},
    })
    nomes = _nomes(cenario.diario)
    assert "body_artifact" not in nomes
    assert nomes[-1] == "pipe.execute"


async def test_falha_ao_registrar_o_body_nao_impede_a_conclusao(cenario, caplog):
    cenario.body_falha = RuntimeError("banco fora")
    body_ref = {"s3_key": f"webhook-responses/ws-1/{RUN}/body.json"}

    with caplog.at_level("ERROR"):
        await RES._handle_job_result(EX, {
            "job_id": RUN, "run_id": RUN, "status": "ok",
            "stats": {"__response__": {"status": 200, "body_ref": body_ref}},
        })

    assert _nomes(cenario.diario)[-1] == "pipe.execute"
    assert (
        "Falha ao registrar Artifact de webhook response (run=run-1): banco fora"
        in _mensagens(caplog)
    )


# ── Validação e truncagem de stats/error ─────────────────────────────────────


async def test_truncagem_que_levou_as_chaves_de_controle_vira_erro_no_webhook(cenario):
    """Executor (novo) que truncou `stats` até sem o `__response__`: o webhook
    recebe um erro explícito em vez de esperar o timeout."""
    stats = {STATS_TRUNCADO: True, STATS_TAMANHO_ORIGINAL: 20_000_000, STATS_CONTROLE_DESCARTADO: True}

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    d = cenario.diario
    raw, res = _run_result(d)
    assert raw == _run_result_esperado(res, status="success", stats_json=json.dumps(stats))
    assert _unico(d, "lpush", WEBHOOK)[2] == json.dumps({
        "job_status": "error",
        "error": (
            "Resposta do workflow excedeu o limite de 20000000 bytes no transporte "
            "executor→servidor. Reduza o tamanho do body (ex: compactar geometria, "
            "paginar resultados) ou consuma via runner assíncrono."
        ),
        "response": None,
    })
    # O desfecho do RUN continua sucesso: só o body é que não coube.
    raw_ev, ev = _conclusao(d)
    assert raw_ev == _conclusao_esperada(ev, level="info", status="completed")


async def test_truncagem_que_preservou_o_response_entrega_o_body(cenario):
    resposta = {"status": 200, "body": "ok"}
    stats = {STATS_TRUNCADO: True, STATS_TAMANHO_ORIGINAL: 99, "__response__": resposta}

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    assert _unico(cenario.diario, "lpush", WEBHOOK)[2] == json.dumps(
        {"job_status": "ok", "error": None, "response": resposta},
    )


async def test_stats_acima_do_teto_e_reduzido_antes_de_todos_os_destinos(cenario):
    """O servidor reaplica a truncagem do protocolo: os stats por nó saem, as
    chaves de controle ficam — o webhook ainda recebe a resposta."""
    resposta = {"status": 200, "body": "ok"}
    stats = {f"node-{i}": {"rows": "x" * 2000} for i in range(2500)}
    stats["__response__"] = resposta
    tamanho = len(json.dumps(stats, default=str))
    assert tamanho > P._MAX_JOB_STATS_BYTES

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    raw, res = _run_result(cenario.diario)
    reduzido = {"__response__": resposta, STATS_TRUNCADO: True, STATS_TAMANHO_ORIGINAL: tamanho}
    assert raw == _run_result_esperado(res, status="success", stats_json=json.dumps(reduzido, default=str))
    assert _unico(cenario.diario, "lpush", WEBHOOK)[2] == json.dumps(
        {"job_status": "ok", "error": None, "response": resposta},
    )


async def test_response_grande_demais_derruba_o_controle_e_avisa_o_webhook(cenario):
    stats = {"__response__": {"status": 200, "body": "x" * (P._MAX_JOB_STATS_BYTES + 10)}}
    tamanho = len(json.dumps(stats, default=str))

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    raw, res = _run_result(cenario.diario)
    marcas = {STATS_TRUNCADO: True, STATS_TAMANHO_ORIGINAL: tamanho, STATS_CONTROLE_DESCARTADO: True}
    assert raw == _run_result_esperado(res, status="success", stats_json=json.dumps(marcas))
    webhook = json.loads(_unico(cenario.diario, "lpush", WEBHOOK)[2])
    assert webhook["job_status"] == "error"
    assert webhook["response"] is None
    assert f"limite de {tamanho} bytes" in webhook["error"]


async def test_stats_que_nao_e_objeto_vira_vazio(cenario):
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": [1, 2]})
    raw, res = _run_result(cenario.diario)
    assert raw == _run_result_esperado(res, status="success", stats_json="{}")
    assert not [cmd for cmd in cenario.diario if WEBHOOK in cmd]


async def test_stats_recursivo_marca_controle_descartado(cenario):
    stats: dict = {"n1": {}}
    stats["n1"]["eu"] = stats

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    raw, res = _run_result(cenario.diario)
    marcas = {STATS_TRUNCADO: True, STATS_CONTROLE_DESCARTADO: True}
    assert raw == _run_result_esperado(res, status="success", stats_json=json.dumps(marcas))
    assert "limite de ? bytes" in json.loads(_unico(cenario.diario, "lpush", WEBHOOK)[2])["error"]


async def test_error_nao_textual_e_gigante_e_contido_em_todos_os_destinos(cenario):
    erro = {"trace": "y" * 20_000}
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "error", "error": erro})

    contido = repr(erro)[:P._MAX_JOB_ERROR_CHARS] + "…[truncado pelo servidor]"
    d = cenario.diario
    assert json.loads(d[1][3])["error"] == contido[:500]
    _, res = _run_result(d)
    assert res["error_message"] == contido
    assert json.loads(_unico(d, "lpush", WEBHOOK)[2])["error"] == contido
    _, ev = _conclusao(d)
    assert ev["error"] == contido


async def test_frame_grande_serializa_fora_do_loop_com_o_mesmo_resultado(cenario, monkeypatch):
    """Acima do limiar, a contenção de `stats` e o dumps do webhook vão para uma
    thread — e o que chega ao Redis é o mesmo."""
    real = asyncio.to_thread
    em_thread: list[str] = []

    async def _espiao(fn, *a, **kw):
        em_thread.append(fn.__name__)
        return await real(fn, *a, **kw)

    monkeypatch.setattr(asyncio, "to_thread", _espiao)
    resposta = {"status": 200, "body": {"id": 1}}
    stats = {"n1": {}, "__response__": resposta}

    await RES._handle_job_result(
        EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats},
        frame_bytes=RES._JSON_OFFLOAD_THRESHOLD + 1,
    )

    assert em_thread == ["_cap_job_result", "dumps"]
    raw, res = _run_result(cenario.diario)
    assert raw == _run_result_esperado(res, status="success", stats_json=json.dumps(stats))
    assert _unico(cenario.diario, "lpush", WEBHOOK)[2] == json.dumps(
        {"job_status": "ok", "error": None, "response": resposta},
    )


async def test_frame_pequeno_nao_usa_thread(cenario, monkeypatch):
    em_thread: list = []

    async def _espiao(fn, *a, **kw):  # pragma: no cover - não pode ser chamado
        em_thread.append(fn)
        return fn(*a, **kw)

    monkeypatch.setattr(asyncio, "to_thread", _espiao)
    await RES._handle_job_result(EX, {
        "job_id": RUN, "run_id": RUN, "status": "ok", "stats": {"__response__": {"status": 200}},
    }, frame_bytes=10)
    assert em_thread == []


# ── Idempotência, posse e limites ────────────────────────────────────────────


@pytest.mark.parametrize("terminal", ["success", "failed", "cancelled"])
async def test_job_result_repetido_de_run_ja_fechado_nao_grava_nada(cenario, caplog, terminal):
    """Reentrega pelo outbox (executor antigo ou novo): o primeiro fecha o run,
    o segundo encontra a linha terminal e sai sem tocar no Redis."""
    msg = {"type": "job_result", "job_id": RUN, "run_id": RUN, "status": "ok", "stats": {"n1": {}}}
    await RES._handle_job_result(EX, dict(msg))
    primeira = list(cenario.diario)
    assert "lpush" in _nomes(primeira)

    cenario.diario.clear()
    cenario.linha = (f"executor:{EX}", terminal, None)
    with caplog.at_level("INFO"):
        await RES._handle_job_result(EX, dict(msg))

    assert cenario.diario == [("snapshot", RUN)]
    assert (
        "Job 'run-1' (run 'run-1'): run já está em estado terminal — resultado "
        "ignorado (idempotência)."
    ) in _mensagens(caplog)


async def test_memo_de_recusa_nega_sem_ler_o_banco(cenario, caplog):
    cenario.conn.run_auth_cache[RUN] = (False, time.monotonic() + 60)

    with caplog.at_level("WARNING"):
        await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})

    assert cenario.diario == []
    assert (
        "Executor 'ex-1' tentou reportar job_result para run 'run-1' que não lhe "
        "pertence — rejeitado."
    ) in _mensagens(caplog)


async def test_memo_de_recusa_vencido_volta_a_ler_o_banco(cenario):
    cenario.conn.run_auth_cache[RUN] = (False, time.monotonic() - 1)
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})
    assert cenario.diario[0] == ("snapshot", RUN)
    assert "lpush" in _nomes(cenario.diario)


@pytest.mark.parametrize("host", ["executor:ex-2", None])
async def test_run_que_nao_e_deste_executor_e_recusado_e_memorizado(cenario, caplog, host):
    cenario.linha = (host, "running", None) if host else None

    with caplog.at_level("WARNING"):
        await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})

    assert cenario.diario == [("snapshot", RUN)]
    ok, prazo = cenario.conn.run_auth_cache[RUN]
    assert ok is False
    assert 0 < prazo - time.monotonic() <= RES._RUN_AUTH_TTL_DENY
    assert (
        f"Executor 'ex-1' tentou reportar job_result para run 'run-1' que não lhe "
        f"pertence (host={host}) — rejeitado."
    ) in _mensagens(caplog)


async def test_sem_job_id_nao_toca_em_nada(cenario, caplog):
    with caplog.at_level("WARNING"):
        await RES._handle_job_result(EX, {"run_id": RUN, "status": "ok"})
    assert cenario.diario == []
    assert "Executor 'ex-1' enviou job_result sem job_id." in _mensagens(caplog)


def _fechamento_inconclusivo(diario, motivo: str) -> None:
    """O pipeline único de `_fechar_run_inconclusivo`, conferido byte a byte."""
    mensagem = f"Resultado do executor não pôde ser processado: {motivo}"
    assert _nomes(diario)[-8:] == [
        "pipe.lpush", "pipe.rpush", "pipe.ltrim", "pipe.expire", "pipe.publish",
        "pipe.lpush", "pipe.expire", "pipe.execute",
    ]
    cmds = diario[-8:]
    assert cmds[0][1] == "run_results"
    resultado = json.loads(cmds[0][2])
    assert cmds[0][2] == json.dumps({
        "task_id":          RUN,
        "status":           "failed",
        "error_message":    mensagem,
        "error_category":   "internal",
        "retryable":        True,
        "end_time":         resultado["end_time"],
        "duration_seconds": None,
        "stats":            {},
    })
    evento = json.loads(cmds[1][2])
    assert cmds[1][2] == json.dumps({
        "run_id":      RUN,
        "node":        WORKFLOW_COMPLETE_NODE,
        "kind":        "lifecycle",
        "level":       "error",
        "status":      "failed",
        "timestamp":   evento["timestamp"],
        "duration_ms": None,
        "error":       mensagem,
        "extra":       {"error_category": "internal", "retryable": True},
    })
    # O evento carimba o MESMO instante do fim gravado no resultado.
    assert evento["timestamp"] == datetime.fromisoformat(resultado["end_time"]).timestamp()
    assert cmds[1:5] == _pipeline_da_conclusao(cmds[1][2])[:4]
    assert cmds[5] == ("pipe.lpush", WEBHOOK, json.dumps(
        {"job_status": "error", "error": mensagem, "response": None},
    ))
    assert cmds[6] == ("pipe.expire", WEBHOOK, 300)


async def test_rate_limit_com_posse_provada_fecha_o_run_como_falho(cenario, monkeypatch, caplog):
    monkeypatch.setattr(RES, "_rate_allowed", lambda *_a: False)
    cenario.conn.run_auth_cache[RUN] = (True, time.monotonic() + 60)

    with caplog.at_level("ERROR"):
        await RES._handle_job_result(EX, {"job_id": "job-x", "run_id": RUN, "status": "ok"})

    # Nem chega a ler o banco: o descarte vem antes da autorização.
    assert "snapshot" not in _nomes(cenario.diario)
    _fechamento_inconclusivo(cenario.diario, "rate limit de job_result")
    assert (
        f"Executor 'ex-1': job_result do job 'job-x' descartado por rate limit "
        f"(>{P._JOB_RESULT_RATE_LIMIT}/{P._RATE_WINDOW:.0f}s)."
    ) in _mensagens(caplog)


async def test_rate_limit_sem_posse_provada_so_descarta(cenario, monkeypatch):
    monkeypatch.setattr(RES, "_rate_allowed", lambda *_a: False)
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})
    assert cenario.diario == []


async def test_banco_fora_retenta_e_fecha_o_run_com_posse_provada(cenario, caplog):
    cenario.linha = RuntimeError("pool esgotado")
    cenario.conn.run_auth_cache[RUN] = (True, time.monotonic() + 60)

    with caplog.at_level("ERROR"):
        await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})

    assert _nomes(cenario.diario)[:RES._JOB_RESULT_DB_RETRIES] == ["snapshot"] * RES._JOB_RESULT_DB_RETRIES
    assert "setex" not in _nomes(cenario.diario)
    _fechamento_inconclusivo(cenario.diario, "banco indisponível (pool esgotado)")
    assert cenario.conn.db_auth_cooldown_until > time.monotonic()
    assert (
        "Não foi possível ler o run 'run-1' para o job_result do executor 'ex-1': "
        "pool esgotado — resultado descartado (fail-closed)."
    ) in _mensagens(caplog)


async def test_banco_fora_sem_posse_provada_nao_fecha_nada(cenario):
    cenario.linha = RuntimeError("pool esgotado")
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})
    assert set(_nomes(cenario.diario)) == {"snapshot"}
    assert cenario.conn.db_auth_cooldown_until > time.monotonic()


# ── Um destino que falha não derruba os seguintes ────────────────────────────


@pytest.mark.parametrize(
    ("falha", "mensagem", "sobram"),
    [
        (
            lambda cmd: cmd[0] == "setex",
            "Erro ao persistir resultado do job 'run-1' no Redis: redis recusou setex",
            ["snapshot", "lpush", "lpush", "expire", "pipe.rpush"],
        ),
        (
            lambda cmd: cmd[0] == "lpush" and cmd[1] == "run_results",
            "Erro ao publicar run_results para run 'run-1': redis recusou lpush",
            ["snapshot", "setex", "lpush", "expire", "pipe.rpush"],
        ),
        (
            lambda cmd: cmd[0] == "lpush" and cmd[1] == WEBHOOK,
            "Erro ao publicar webhook_response para run 'run-1': redis recusou lpush",
            ["snapshot", "setex", "lpush", "pipe.rpush"],
        ),
        (
            lambda cmd: cmd[0] == "pipe.execute",
            "Erro ao publicar __workflow_complete__ para run 'run-1': redis recusou pipe.execute",
            ["snapshot", "setex", "lpush", "lpush", "expire"],
        ),
    ],
)
async def test_falha_de_um_destino_nao_impede_os_seguintes(cenario, caplog, falha, mensagem, sobram):
    cenario.falhar = falha
    with caplog.at_level("ERROR"):
        await RES._handle_job_result(EX, {
            "job_id": RUN, "run_id": RUN, "status": "error", "error": "boom",
        })
    assert _nomes(cenario.diario)[:len(sobram)] == sobram
    assert mensagem in _mensagens(caplog)
