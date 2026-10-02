# tests/unit/test_reducao_node_event.py
"""Redução de node_event acima do teto: uma regra só nos dois lados do fio.

Executor e servidor tinham cada um a sua cópia, com regras diferentes. O
executor (antes de enviar) preservava `duration_ms` e as linhas de stdout que
coubessem, mas jogava fora o `extra` inteiro; o servidor (antes do Redis)
cortava só as chaves pesadas do `extra` e mantinha `output_columns`. Como o teto
é o mesmo, o executor já entregava o evento reduzido e a regra do servidor
nunca rodava para um executor honesto: um `completed` com traceback grande
chegava ao painel sem a sugestão de coluna do editor.
"""
import json

from app.api.routers.executor_ws import resultados as RES
from executor.connection import _dumps_event
from flow.utils.publisher.reducao import TETO_NODE_EVENT_BYTES as TETO
from flow.utils.publisher.reducao import TETO_POR_CAMPO, reduzir_node_event


def _completed_com_traceback_grande() -> tuple[dict, dict]:
    colunas = {"result": [f"col_{i}" for i in range(120)]}
    evento = {
        "type": "node_event", "run_id": "run-1", "node": "n1", "status": "completed",
        "kind": "lifecycle", "level": "info", "timestamp": 123.0, "duration_ms": 42.5,
        "error": None,
        "extra": {
            "node_name": "Join", "node_type": "join", "output_keys": ["result"],
            "output_columns": colunas,
            "traceback": "Traceback (most recent call last):\n" + "  linha\n" * 12_000,
        },
    }
    assert len(json.dumps(evento)) > TETO
    return evento, colunas


# ── O bug: a redução do executor perdia output_columns ───────────────────────

def test_completed_com_traceback_grande_mantem_output_columns_na_reducao_do_executor():
    evento, colunas = _completed_com_traceback_grande()

    bruto = _dumps_event(evento)

    assert len(bruto) <= TETO
    reduzido = json.loads(bruto)
    assert (reduzido.get("extra") or {}).get("output_columns") == colunas, (
        "o executor reduziu o evento e a sugestão de coluna do editor sumiu"
    )
    assert "traceback" not in reduzido["extra"], "o peso tinha que sair"
    assert reduzido["extra"]["node_name"] == "Join"
    assert reduzido["type"] == "node_event"        # sem isso o servidor não roteia
    assert reduzido["duration_ms"] == 42.5
    assert reduzido["__truncated__"] is True
    assert reduzido["__original_size__"] == len(json.dumps(evento))


def test_failed_com_erro_gigante_chega_com_o_erro_encurtado_e_a_categoria():
    """O executor derrubava `error` e `extra` juntos: o nó aparecia falho no
    painel sem mensagem nenhuma e sem dizer se valia repetir."""
    evento = {
        "type": "node_event", "run_id": "run-1", "node": "n1", "status": "failed",
        "kind": "lifecycle", "level": "error", "timestamp": 123.0, "duration_ms": 7.0,
        "error": "E" * 100_000,
        "extra": {"node_name": "Buffer", "error_category": "runtime", "retryable": False,
                  "traceback": "tb"},
    }

    reduzido = json.loads(_dumps_event(evento))

    assert (reduzido.get("error") or "").startswith("E" * 1_000), "a mensagem de erro sumiu"
    assert len(reduzido["error"]) < 10_000
    assert reduzido["extra"]["error_category"] == "runtime"
    assert reduzido["extra"]["retryable"] is False


# ── O servidor reaplica como defesa, com as regras dos dois lados ────────────

def test_evento_reduzido_pelo_executor_passa_pelo_servidor_sem_perder_mais_nada():
    evento, colunas = _completed_com_traceback_grande()
    enviado = json.loads(_dumps_event(evento))

    publicado = json.loads(RES._serialize_node_event("ex-1", enviado))

    assert publicado == {k: v for k, v in enviado.items() if k != "type"}
    assert (publicado.get("extra") or {}).get("output_columns") == colunas


def test_servidor_preserva_as_linhas_de_stdout_de_evento_que_chega_grande():
    """Executor com bug (ou antigo demais para reduzir): o servidor jogava fora
    `lines` inteiro como chave pesada e a aba de saída do nó ficava vazia."""
    msg = {
        "type": "node_event", "run_id": "r", "node": "n", "kind": "stdout",
        "status": "log", "level": "info", "timestamp": 1.0,
        "extra": {"lines": ["y" * 500 for _ in range(400)]},
    }

    bruto = RES._serialize_node_event("ex-1", msg)

    assert len(bruto) <= TETO
    linhas = (json.loads(bruto).get("extra") or {}).get("lines") or []
    assert linhas[:3] == ["y" * 500] * 3, "as linhas que cabiam foram jogadas fora"
    assert "nao couberam" in linhas[-1], "o corte tem que ser marcado"


def test_servidor_reduzindo_aos_campos_de_controle_preserva_duration_ms():
    msg = {
        "type": "node_event", "run_id": "r", "node": "n", "kind": "lifecycle",
        "status": "completed", "level": "info", "timestamp": 1.0, "duration_ms": 12.0,
        "blob": "x" * 100_000,
    }

    reduzido = json.loads(RES._serialize_node_event("ex-1", msg))

    assert "blob" not in reduzido
    assert reduzido.get("duration_ms") == 12.0, "o painel perdia a duração do nó"


# ── Degraus da regra única ────────────────────────────────────────────────────

def test_degrau_1_serializa_o_extra_leve_com_o_default_do_executor():
    """O `extra` que sobra pode ter Timestamp/numpy no executor: sem o `default`
    dele o dumps levantava TypeError e o sender reciclava o evento em laço."""
    from datetime import datetime

    evento = {
        "type": "node_event", "run_id": "r", "node": "n", "status": "completed",
        "kind": "lifecycle", "timestamp": 1.0,
        "extra": {"quando": datetime(2026, 9, 30, 12, 0), "traceback": "t" * 70_000},
    }

    reduzido = json.loads(_dumps_event(evento))

    assert reduzido["extra"] == {"quando": "2026-09-30T12:00:00"}


def test_evento_que_cabe_volta_intacto():
    evento = {"run_id": "r", "node": "n", "status": "completed", "extra": {"branch": "a"}}
    payload = json.dumps(evento)
    assert reduzir_node_event(evento, payload) is payload


def test_degrau_2_ainda_guarda_as_linhas_de_stdout():
    """Nem sem o peso o evento cabe (campo de controle hostil): cai para os
    campos de controle coagidos, e as linhas que couberem voltam junto."""
    evento = {
        "type": "node_event", "run_id": "r", "node": {"lixo": "z" * 80_000},
        "kind": "stdout", "status": "log", "level": "info", "timestamp": 1.0,
        "extra": {"lines": [f"linha {i}" for i in range(50)]},
    }

    bruto = _dumps_event(evento)

    assert len(bruto) <= TETO
    reduzido = json.loads(bruto)
    assert len(reduzido["node"]) <= TETO_POR_CAMPO
    assert reduzido["extra"]["lines"] == [f"linha {i}" for i in range(50)]


def test_rede_de_seguranca_mantem_o_type_que_roteia_a_mensagem():
    """Sem `type` o servidor não sabe o que fazer com a mensagem e a descarta."""
    evento = {
        "type": "node_event", "run_id": "r", "node": "n", "status": "failed",
        "kind": {"k": "x" * 1_000}, "level": {"l": "y" * 1_000}, "timestamp": 1.0,
    }
    payload = json.dumps(evento)

    bruto = reduzir_node_event(evento, payload, teto=800)

    assert len(bruto) <= 800
    reduzido = json.loads(bruto)
    assert reduzido["type"] == "node_event"
    assert (reduzido["run_id"], reduzido["node"], reduzido["status"]) == ("r", "n", "failed")
    assert reduzido["__truncated__"] is True
