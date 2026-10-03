# tests/unit/test_despacho_caracterizacao.py
"""
Characterization of `_dispatch_job`: the ORDER of the effects and the messages.

The dispatch writes to the database, encrypts, talks to the executor, closes the
run and emits the `dispatch_event` — and the order is a contract: the host has
to be stored before the send (it is what authorizes the executor to report the
run), the closing comes before the event, and the `except` safety net goes
through every `raise`. These tests record each effect in a single list and
compare the whole sequence, so that splitting the function changes nothing about
what happens nor when it happens.

What already had coverage (and stays in the original files): labels in the
INSERT and categories (test_run_trigger_source.py), cancellation in the middle
of the dispatch against a real database (test_fechamento_de_run.py), barrier and
`dispatch_tier` (test_policy_routing.py), send_job blowing up
(test_fix_consumer_services.py), ACK before the commit (test_na_fila_eterno.py).
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NoExecutorAvailableError
from app.services import workflow_execution_service as wes
from app.services.fechamento_de_run import ABERTOS, REPETIVEL


# ── Factories ─────────────────────────────────────────────────────────────────

def _wf(workspace_id="ws-1"):
    wf = MagicMock()
    wf.id_hash = "wf-1"
    wf.workspace_id = workspace_id
    # One pin with metadata (passes) and one orphan (left out of the envelope).
    wf.pinned_outputs = {"n1": {"__pin_s3_key__": "k1"}, "orfao": {"__pin_s3_key__": "k2"}}
    wf.pin_metadata = {"n1": {"expires_at": None}}
    return wf


def _executor(id_hash, name=None):
    ag = MagicMock()
    ag.id_hash, ag.name, ag.public_key = id_hash, name, f"pem-{id_hash}"
    return ag


_DEFINICAO = {"id": "raiz", "nodes": [{"id": "r", "name": "Response"}], "edges": []}


class _Banco:
    """Fake session that records INSERT, commit (with the host stored at that
    instant) and the pending→running UPDATE in the same list as the other effects."""

    def __init__(self, efeitos, *, rowcount=1, falhar_no_commit=None):
        self.efeitos = efeitos
        self.run = None
        self.rowcount = rowcount
        self.falhar_no_commit = falhar_no_commit
        self.commits = 0

    def add(self, obj):
        self.run = obj
        self.efeitos.append(("insert", obj.host, obj.dispatch_tier, obj.status))

    async def commit(self):
        self.commits += 1
        if self.falhar_no_commit == self.commits:
            raise RuntimeError("banco caiu")
        self.efeitos.append(("commit", self.run.host))

    async def execute(self, stmt):
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        self.efeitos.append(("update", sql.split()[0], "status IN ('pending', 'running')" in sql))
        return MagicMock(rowcount=self.rowcount)

    async def rollback(self):
        self.efeitos.append(("rollback",))


@pytest.fixture
def cenario(monkeypatch):
    """Everything the dispatch touches, recorded in `efeitos` in the order it happens."""
    efeitos: list = []
    estado = {
        "envios": {},          # executor_id -> True | False | Exception
        "falha_cifra": set(),  # executores cuja cifra levanta RuntimeError
        "aviso_falha": False,  # send_json (cancel) levanta
        "cifras": [],          # kwargs of each build_job_message
    }

    async def _credenciais(definicao, *, pre_resolved=None):
        efeitos.append(("credenciais", definicao.get("id"), pre_resolved))
        return {**definicao, "injetado": True}

    def _cifra(**kwargs):
        efeitos.append(("cifra", kwargs["executor_id"]))
        estado["cifras"].append(kwargs)
        if kwargs["executor_id"] in estado["falha_cifra"]:
            raise RuntimeError("chave inválida")
        return {"envelope": kwargs["executor_id"]}

    async def _thread(func, /, *args, **kwargs):
        efeitos.append(("thread", getattr(func, "__name__", "?")))
        return func(*args, **kwargs)

    async def _envio(executor_id, _msg):
        efeitos.append(("envio", executor_id))
        comportamento = estado["envios"][executor_id]
        if isinstance(comportamento, Exception):
            raise comportamento
        return comportamento

    async def _aviso(executor_id, msg):
        efeitos.append(("aviso", executor_id, msg))
        if estado["aviso_falha"]:
            raise RuntimeError("socket fechado")
        return True

    async def _fechar(db, runs, *, de, para, mensagem, categoria, extra=None, **_k):
        efeitos.append(("fechar", para, categoria, mensagem, extra, de))
        fechados = [r for r in runs if r.status in de]
        for r in fechados:
            r.status = para
        return fechados

    def _evento(**kwargs):
        assert isinstance(kwargs.pop("decision_ms"), float)
        efeitos.append(("evento", kwargs.pop("outcome"), kwargs))

    reg = MagicMock()
    reg.send_job = AsyncMock(side_effect=_envio)
    reg.send_json = AsyncMock(side_effect=_aviso)

    monkeypatch.setattr(wes, "inject_credentials", _credenciais)
    monkeypatch.setattr(wes, "build_job_message", _cifra)
    monkeypatch.setattr(wes.asyncio, "to_thread", _thread)
    monkeypatch.setattr(wes, "executor_registry", reg)
    monkeypatch.setattr(wes, "fechar_runs", _fechar)
    monkeypatch.setattr(wes, "_log_dispatch_event", _evento)
    return efeitos, estado


# ── Happy path with failover ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sequencia_completa_com_failover(cenario):
    """ag-1 refuses, ag-2's encryption fails, ag-3 accepts: the INSERT carries the
    first one's host; the credentials (root and sub-workflow) and the
    serialization come after the commit; only the failover that REACHES the send
    rewrites the host, and before sending; the conditional UPDATE and the commit
    come after the accepted send."""
    efeitos, estado = cenario
    estado["envios"] = {"ag-1": False, "ag-3": True}
    estado["falha_cifra"] = {"ag-2"}
    cadeia = wes.CandidateList(
        [_executor("ag-1"), _executor("ag-2"), _executor("ag-3")],
        tiers={"ag-1": "primary", "ag-2": "fallback", "ag-3": "pool"},
        allowed={"ag-1", "ag-2", "ag-3"}, mode="dedicated_pool",
    )
    db = _Banco(efeitos)
    wf = _wf()

    result = await wes._dispatch_job(
        wf, _DEFINICAO, cadeia, {"x": 1}, True, db=db,
        pre_resolved={"c": {}}, subworkflow_definitions={"sub-1": {"id": "sub", "nodes": []}},
    )

    assert efeitos == [
        ("insert", "executor:ag-1", "primary", "pending"),
        ("commit", "executor:ag-1"),
        ("credenciais", "raiz", {"c": {}}),
        ("credenciais", "sub", {"c": {}}),
        ("thread", "<lambda>"),
        ("cifra", "ag-1"),
        ("envio", "ag-1"),
        ("cifra", "ag-2"),
        ("cifra", "ag-3"),
        ("commit", "executor:ag-3"),
        ("envio", "ag-3"),
        ("update", "UPDATE", True),
        ("commit", "executor:ag-3"),
        ("evento", "dispatched", {
            "wf": wf, "mode": "dedicated_pool", "candidates_total": 3,
            "chosen": "ag-3", "tier": "pool", "failovers": 2, "run_id": result.id,
        }),
    ]
    assert result.id == db.run.task_id and result.has_response_node is True
    assert (db.run.status, db.run.host, db.run.dispatch_tier) == ("running", "executor:ag-3", "pool")


@pytest.mark.asyncio
async def test_envelope_e_argumentos_da_cifra(cenario):
    """The payload is serialized ONCE (the same `bytes` for each candidate) and
    carries what the executor needs; an absent `workspace_id` becomes an empty string."""
    efeitos, estado = cenario
    estado["envios"] = {"ag-1": False, "ag-2": True}
    db = _Banco(efeitos)

    result = await wes._dispatch_job(
        _wf(workspace_id=None), _DEFINICAO, [_executor("ag-1", "maquina"), _executor("ag-2")],
        None, False, db=db, disabled_nodes=["Velho"],
    )

    primeira, segunda = estado["cifras"]
    assert primeira["payload"] is segunda["payload"]
    assert {k: v for k, v in primeira.items() if k != "payload"} == {
        "executor_id": "ag-1", "workspace_id": "", "agent_x25519_pub_pem": "pem-ag-1",
        "job_type": "run_workflow", "job_id": result.id,
    }
    assert json.loads(primeira["payload"]) == {
        "workflow_definition": {**_DEFINICAO, "injetado": True},
        "workflow_hash": "wf-1",
        "run_id": result.id,
        "params": {},
        "workspace_id": None,
        "debug_mode": False,
        "pinned_outputs": {"n1": {"__pin_s3_key__": "k1"}},
        "pin_metadata": {"n1": {"expires_at": None}},
        "disabled_nodes": ["Velho"],
        "subworkflow_definitions": {},
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("limiar, cifra_em_thread", [(1, True), (10**9, False)])
async def test_cifra_vai_para_thread_so_acima_do_limiar(cenario, monkeypatch, limiar, cifra_em_thread):
    efeitos, estado = cenario
    estado["envios"] = {"ag-1": False, "ag-2": True}
    monkeypatch.setattr(wes, "_LIMIAR_CIFRA_EM_THREAD", limiar)

    await wes._dispatch_job(_wf(), _DEFINICAO, [_executor("ag-1"), _executor("ag-2")], {}, False, db=_Banco(efeitos))

    threads = [e[1] for e in efeitos if e[0] == "thread"]
    # Serialization always goes to the thread; encryption, per candidate, only above the threshold.
    assert threads == (["<lambda>", "_cifra", "_cifra"] if cifra_em_thread else ["<lambda>"])


# ── No candidate accepts: closing, event, exception ─────────────────────────

@pytest.mark.asyncio
async def test_esgotado_com_mensagem_da_politica_e_ultimo_motivo(cenario):
    efeitos, estado = cenario
    estado["envios"] = {"abcdef-12345": False, "ag-2": RuntimeError("is_full quebrado")}
    cadeia = wes.CandidateList(
        [_executor("abcdef-12345", "maquina"), _executor("ag-2")],
        tiers={"abcdef-12345": "primary"}, allowed=None, mode="isolated",
        exhausted_message="Workspace isolado: nenhum disponível.", exhausted_category="no_dedicated_executor",
    )
    db = _Banco(efeitos)
    wf = _wf()

    with pytest.raises(NoExecutorAvailableError) as exc:
        await wes._dispatch_job(wf, _DEFINICAO, cadeia, {}, False, db=db)

    mensagem = ("Workspace isolado: nenhum disponível. Último motivo: "
                "Erro ao enviar job para 'ag-2': is_full quebrado")
    assert efeitos[-3:] == [
        ("fechar", "failed", "no_executor", mensagem, REPETIVEL, ABERTOS),
        ("evento", "all_refused", {
            "wf": wf, "mode": "isolated", "candidates_total": 2, "chosen": None,
            "tier": None, "failovers": 2, "category": "no_dedicated_executor", "run_id": db.run.task_id,
        }),
        # The `except` safety net goes through the `raise` of path (4); the run
        # is already closed, so it rewrites nothing.
        ("fechar", "failed", "dispatch", f"Falha no despacho: {mensagem}", None, ABERTOS),
    ]
    assert [e for e in efeitos if e[0] == "envio"] == [("envio", "abcdef-12345"), ("envio", "ag-2")]
    assert (exc.value.detail, exc.value.category, exc.value.run_id) == (
        mensagem, "no_dedicated_executor", db.run.task_id,
    )
    assert db.run.status == "failed"


@pytest.mark.asyncio
@pytest.mark.parametrize("comportamento, falha_cifra, mensagem", [
    (False, False, "Executor 'maquina@12345' não aceitou o job (fila cheia ou desconectado)."),
    (RuntimeError("boom"), False, "Erro ao enviar job para 'maquina@12345': boom"),
    (True, True, "Falha ao cifrar job para 'maquina@12345': chave inválida"),
])
async def test_ultimo_motivo_por_tipo_de_recusa(cenario, comportamento, falha_cifra, mensagem):
    efeitos, estado = cenario
    estado["envios"] = {"abcdef-12345": comportamento}
    if falha_cifra:
        estado["falha_cifra"] = {"abcdef-12345"}

    with pytest.raises(NoExecutorAvailableError) as exc:
        await wes._dispatch_job(_wf(), _DEFINICAO, [_executor("abcdef-12345", "maquina")], {}, False, db=_Banco(efeitos))

    assert exc.value.detail == mensagem and exc.value.category == "no_executor"
    assert [e[3] for e in efeitos if e[0] == "fechar"][0] == mensagem


@pytest.mark.asyncio
async def test_sem_nome_o_rotulo_e_o_id(cenario):
    efeitos, estado = cenario
    estado["envios"] = {"ag-sem-nome": False}
    with pytest.raises(NoExecutorAvailableError) as exc:
        await wes._dispatch_job(_wf(), _DEFINICAO, [_executor("ag-sem-nome")], {}, False, db=_Banco(efeitos))
    assert exc.value.detail == "Executor 'ag-sem-nome' não aceitou o job (fila cheia ou desconectado)."


@pytest.mark.asyncio
@pytest.mark.parametrize("candidatos, mensagem, categoria", [
    ([], "Nenhum executor aceitou o job.", "no_executor"),
    (wes.CandidateList([], exhausted_message="Nenhum executor do pool.", exhausted_category="no_pool_executor"),
     "Nenhum executor do pool.", "no_pool_executor"),
])
async def test_lista_vazia_fecha_sem_host(cenario, candidatos, mensagem, categoria):
    efeitos, _ = cenario
    db = _Banco(efeitos)
    wf = _wf()

    with pytest.raises(NoExecutorAvailableError) as exc:
        await wes._dispatch_job(wf, _DEFINICAO, candidatos, {}, False, db=db)

    assert efeitos == [
        ("insert", None, None, "pending"),
        ("commit", None),
        ("credenciais", "raiz", None),
        ("thread", "<lambda>"),
        ("fechar", "failed", "no_executor", mensagem, REPETIVEL, ABERTOS),
        ("evento", "all_refused", {
            "wf": wf, "mode": None, "candidates_total": 0, "chosen": None,
            "tier": None, "failovers": 0, "category": categoria, "run_id": db.run.task_id,
        }),
        ("fechar", "failed", "dispatch", f"Falha no despacho: {mensagem}", None, ABERTOS),
    ]
    assert (exc.value.category, exc.value.run_id) == (categoria, db.run.task_id)


# ── Isolation barrier ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_barreira_depois_de_um_failover(cenario):
    """The intruder is the SECOND: the first was already tried; the intruder is not
    encrypted for, the host is not rewritten for it, and the event counts the
    failover."""
    efeitos, estado = cenario
    estado["envios"] = {"geo-01": False}
    cadeia = wes.CandidateList(
        [_executor("geo-01"), _executor("pool-x")], tiers={"geo-01": "primary", "pool-x": "pool"},
        allowed={"geo-01"}, mode="isolated",
    )
    db = _Banco(efeitos)
    wf = _wf()

    with pytest.raises(NoExecutorAvailableError) as exc:
        await wes._dispatch_job(wf, _DEFINICAO, cadeia, {}, False, db=db)

    barreira = ("Barreira de isolamento: o roteamento escolheu um executor fora da "
                "política do workspace. O job não foi enviado.")
    assert efeitos[4:] == [
        ("cifra", "geo-01"),
        ("envio", "geo-01"),
        ("fechar", "failed", "isolation", barreira, None, ABERTOS),
        ("evento", "isolation_violation", {
            "wf": wf, "mode": "isolated", "candidates_total": 2, "chosen": "pool-x",
            "tier": "pool", "failovers": 1, "category": "isolation_violation", "run_id": db.run.task_id,
        }),
        ("fechar", "failed", "dispatch", f"Falha no despacho: {barreira}", None, ABERTOS),
    ]
    assert (exc.value.category, exc.value.run_id) == ("isolation_violation", db.run.task_id)
    assert db.run.host == "executor:geo-01"


# ── Cancellation that wins the race against the send ─────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("aviso_falha", [False, True])
async def test_cancelado_durante_o_envio_avisa_o_executor_e_devolve(cenario, aviso_falha):
    """UPDATE with no row = the user canceled: the executor that already accepted
    gets the 'cancel' (failing to notify only becomes a log line), the run is not
    promoted and there is no dispatch event nor closing."""
    efeitos, estado = cenario
    estado["envios"] = {"ag-1": True}
    estado["aviso_falha"] = aviso_falha
    db = _Banco(efeitos, rowcount=0)

    result = await wes._dispatch_job(_wf(), _DEFINICAO, [_executor("ag-1")], {}, False, db=db)

    assert efeitos[-4:] == [
        ("envio", "ag-1"),
        ("update", "UPDATE", True),
        ("commit", "executor:ag-1"),
        ("aviso", "ag-1", {"type": "cancel", "job_id": result.id}),
    ]
    assert db.run.status == "pending"
    assert result.id == db.run.task_id and result.has_response_node is True


# ── Infrastructure failures ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_falha_no_insert_sobe_sem_passar_pela_rede_de_seguranca(cenario):
    """The INSERT is OUTSIDE the try: if its commit fails there is no run to close."""
    efeitos, _ = cenario
    db = _Banco(efeitos, falhar_no_commit=1)

    with pytest.raises(RuntimeError, match="banco caiu"):
        await wes._dispatch_job(_wf(), _DEFINICAO, [_executor("ag-1")], {}, False, db=db)

    assert efeitos == [("insert", "executor:ag-1", None, "pending")]


@pytest.mark.asyncio
async def test_falha_ao_regravar_o_host_no_failover_fecha_como_dispatch(cenario):
    efeitos, estado = cenario
    estado["envios"] = {"ag-1": False, "ag-2": True}
    db = _Banco(efeitos, falhar_no_commit=2)   # 1 = INSERT; 2 = failover host

    with pytest.raises(RuntimeError, match="banco caiu"):
        await wes._dispatch_job(_wf(), _DEFINICAO, [_executor("ag-1"), _executor("ag-2")], {}, False, db=db)

    assert efeitos[-3:] == [
        ("envio", "ag-1"),
        ("cifra", "ag-2"),
        ("fechar", "failed", "dispatch", "Falha no despacho: banco caiu", None, ABERTOS),
    ]
    assert ("envio", "ag-2") not in efeitos
