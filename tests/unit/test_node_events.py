"""
Contrato dos eventos de execução de nó (flow.executor.events).

O painel de execução do frontend depende de `kind` (origem: lifecycle/stdout/
debug) e `level` (severidade) serem campos PRÓPRIOS, e não deduzidos de `status`.
Enquanto tudo vivia em `status`, a UI precisava filtrar por negação ("tudo que
não é erro nem print") e não conseguia distinguir stdout de ciclo de vida.

A categoria de erro por nó é o que permite ao painel dizer "corrija a entrada"
em vez de apenas despejar o traceback.
"""
from unittest.mock import MagicMock

import pytest

from flow.executor import events as node_events
from flow.utils.publisher.events import publish_stdout


NODE_DEFS = {"n1": {"name": "Ler CSV", "type": "action"}}


def _publisher():
    return MagicMock(publish_event=MagicMock())


def _kwargs(pub):
    """Normaliza a chamada em kwargs — os helpers misturam posicional e nomeado."""
    args, kwargs = pub.publish_event.call_args
    names = ["run_id", "node", "status", "timestamp", "duration_ms", "error", "extra"]
    merged = dict(zip(names, args))
    merged.update(kwargs)
    return merged


def test_started_e_lifecycle_info():
    pub = _publisher()
    node_events.publish_started(pub, "run-1", "n1", NODE_DEFS)
    call = _kwargs(pub)
    assert call["kind"] == "lifecycle"
    assert call["level"] == "info"
    assert call["status"] == "started"
    assert call["extra"]["node_name"] == "Ler CSV"


def test_completed_sem_drift_e_info():
    pub = _publisher()
    node_events.publish_completed(pub, "run-1", "n1", NODE_DEFS, "completed", 12.5, output_keys=["out"])
    call = _kwargs(pub)
    assert call["kind"] == "lifecycle"
    assert call["level"] == "info"
    assert call["extra"]["output_keys"] == ["out"]
    assert "error_category" not in call["extra"]


def test_schema_drift_eleva_para_warn():
    """Drift não é falha, mas também não é rotina — o painel destaca em âmbar."""
    pub = _publisher()
    node_events.publish_completed(
        pub, "run-1", "n1", NODE_DEFS, "completed", 3.0,
        schema_drift={"missing": ["geometry"], "extra": []},
    )
    call = _kwargs(pub)
    assert call["level"] == "warn"
    assert call["extra"]["schema_drift"]["missing"] == ["geometry"]


@pytest.mark.parametrize("exc, category, retryable", [
    (ValueError("coluna ausente"), "user", False),
    (TimeoutError(), "timeout", True),
    (ConnectionError(), "transient", True),
    (MemoryError(), "resource", False),
])
def test_falha_publica_categoria_e_retryable(exc, category, retryable):
    pub = _publisher()
    node_events.publish_completed(
        pub, "run-1", "n1", NODE_DEFS, "failed", 8.0,
        error=str(exc), traceback_str="Traceback…", exception=exc,
    )
    call = _kwargs(pub)
    assert call["level"] == "error"
    assert call["extra"]["error_category"] == category
    assert call["extra"]["retryable"] is retryable
    # Traceback vai SEMPRE no evento de falha — a UI decide quando mostrar,
    # e passou a mostrar por padrão (antes exigia o modo debug, que precisa ser
    # ligado antes de executar e portanto nunca estava ligado quando faltava).
    assert call["extra"]["traceback"] == "Traceback…"


def test_debug_tem_kind_proprio():
    pub = _publisher()
    node_events.publish_debug(pub, "run-1", "n1", NODE_DEFS, {"a": 1}, {"b": 2})
    call = _kwargs(pub)
    assert call["kind"] == "debug"
    assert call["status"] == "debug"
    assert "debug_output" in call["extra"]


def test_stdout_tem_kind_proprio():
    """O stdout viaja em LOTE e `lines` é a ÚNICA fonte de verdade.

    Um evento por linha de print() estourava a fila de 500 slots do executor
    (compartilhada por todos os jobs e pelo GeoSync) e o rate limit do servidor.
    Já `extra['message']` não existe mais: publicar o mesmo texto duas vezes
    dobrava o payload e um lote de 200 linhas longas passava dos 64 KB de
    `TETO_NODE_EVENT_BYTES`, fazendo o sender reduzir o evento aos campos de
    controle — sem `extra` — e o painel perder as 200 linhas de uma vez.
    """
    pub = _publisher()
    publish_stdout(pub, "run-1", "n1", ["processando 1200 feições", "pronto"])
    call = _kwargs(pub)
    assert call["kind"] == "stdout"
    assert call["level"] == "info"
    assert call["extra"]["lines"] == ["processando 1200 feições", "pronto"]
    assert "message" not in call["extra"], "texto duplicado estoura o teto de 64 KB"


def test_stdout_nunca_derruba_o_no():
    """print() do usuário não pode quebrar a execução se o publisher falhar."""
    pub = MagicMock(publish_event=MagicMock(side_effect=RuntimeError("redis fora")))
    publish_stdout(pub, "run-1", "n1", ["texto"])  # não deve levantar
    publish_stdout(None, "run-1", "n1", ["texto"])
    publish_stdout(pub, "", "n1", ["texto"])
    publish_stdout(pub, "run-1", "n1", [])  # lote vazio não vira evento
