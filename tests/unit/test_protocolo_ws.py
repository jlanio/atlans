# tests/unit/test_protocolo_ws.py
"""Vocabulário do protocolo WS executor ↔ servidor, lado a lado.

O servidor responde com `{"type": "error", "reason": ...}` a toda mensagem que
recusa (JSON inválido, campo obrigatório ausente, capacity inválida, mensagem
antes do handshake, versão não suportada) — "evita loop onde ele aguarda ACK".
Só que `error` não estava na allowlist do executor: a resposta caía em
"Mensagem desconhecida", em DEBUG, e o motivo da recusa só existia no log do
servidor — que o operador do executor, na máquina do cliente, não vê.
"""
import asyncio
import json
import logging

from executor import connection as conn_mod
from executor.connection import ExecutorConnection


class _WSQueEntrega:
    """WebSocket que entrega uma lista fixa de mensagens e grava os envios."""

    def __init__(self, mensagens):
        self._mensagens = [json.dumps(m) for m in mensagens]
        self.enviadas = []

    def __aiter__(self):
        async def _gen():
            for m in self._mensagens:
                yield m
        return _gen()

    async def send(self, raw):
        self.enviadas.append(json.loads(raw))


def _conexao():
    return ExecutorConnection(job_queue=None, result_queue=asyncio.Queue())


def _avisos(caplog) -> list[str]:
    return [
        r.getMessage() for r in caplog.records
        if r.name == "executor.connection" and r.levelno == logging.WARNING
    ]


# ── O bug: a resposta de erro do servidor não chegava a ninguém ──────────────

async def test_executor_registra_em_warning_o_erro_que_o_servidor_devolve(caplog):
    conn = _conexao()
    ws = _WSQueEntrega([{"type": "error", "reason": "invalid_capacity"}])

    with caplog.at_level(logging.DEBUG, logger="executor.connection"):
        await conn._receive_loop(ws)

    assert any("invalid_capacity" in aviso for aviso in _avisos(caplog)), (
        "o executor recebeu a recusa do servidor e não disse nada ao operador"
    )


async def test_erro_do_servidor_leva_o_detalhe_e_nao_muda_o_estado_da_conexao(caplog):
    conn = _conexao()
    ws = _WSQueEntrega([{
        "type": "error", "reason": "invalid_schema",
        "missing_fields": ["max_queue"], "message_type": "capacity",
    }])

    with caplog.at_level(logging.DEBUG, logger="executor.connection"):
        await conn._receive_loop(ws)

    avisos = [a for a in _avisos(caplog) if "invalid_schema" in a]
    assert avisos and "max_queue" in avisos[0], "o detalhe da recusa se perdeu"
    assert ws.enviadas == [], "erro é só registro: nada volta ao servidor"
    assert conn._should_reconnect is True
    assert conn.terminal_deny is None


# ── Truncagem de stats: a regra do servidor e a do executor ──────────────────

def test_truncagem_de_stats_do_executor_informa_o_tamanho_original(monkeypatch):
    """Nem as chaves de controle couberam: `__original_size__` tem de ser o do
    job_result inteiro. O executor gravava ali o tamanho da PRIMEIRA redução —
    o servidor, na mesma situação, grava o original."""
    monkeypatch.setattr(conn_mod, "_MAX_WS_PAYLOAD", 2_000)
    obj = {
        "type": "job_result", "job_id": "j1", "status": "ok",
        "stats": {"__response__": {"body": "r" * 5_000}, "no1": "z" * 20_000},
    }
    original = len(json.dumps(obj))

    stats = json.loads(conn_mod._dumps_result(obj))["stats"]

    assert stats["__control_dropped__"] is True
    assert stats["__original_size__"] == original
