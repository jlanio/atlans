"""
Classificacao de erros de conexao do executor (_classify_connection_error).

Regressao: o executor tratava HTTP 401/403/404 no handshake WS como TERMINAL
(assumia "executor removido") e parava de reconectar — encerrando com exit 0,
que o `restart: on-failure` do Docker nao reinicia. Mas o app NUNCA nega via
status HTTP: todo deny autoritativo chega como WS close code 4401/4403/4404.
Um status HTTP 4xx/5xx no handshake so pode vir da BORDA (Traefik/Cloudflare) e,
durante um deploy, e transitorio (proxy sem rota / backend subindo).

Contrato agora:
  - InvalidStatus (qualquer status HTTP)      -> NAO terminal (retry com backoff)
  - ConnectionClosed com code 4401/4403/4404  -> terminal (deny real do app)
  - ConnectionClosed com code 1006/1001/...   -> NAO terminal (queda transitoria)
  - OSError (connection refused, DNS)         -> NAO terminal
"""
import types

import pytest

from executor.connection import _classify_connection_error


def _invalid_status(status: int):
    from websockets.exceptions import InvalidStatus
    return InvalidStatus(types.SimpleNamespace(status_code=status))


def _conn_closed(code: int):
    from websockets.exceptions import ConnectionClosed
    from websockets.frames import Close
    return ConnectionClosed(Close(code, ""), None)


@pytest.mark.parametrize("status", [401, 403, 404, 502, 503])
def test_http_status_no_handshake_nunca_e_terminal(status):
    """O bug: 404 do Traefik em deploy nao pode derrubar o executor."""
    _msg, _tb, terminal = _classify_connection_error(_invalid_status(status))
    assert terminal is False, f"HTTP {status} no handshake NAO deve ser terminal"


@pytest.mark.parametrize("code", [4401, 4403, 4404])
def test_close_code_4xxx_do_app_e_terminal(code):
    """Deny autoritativo do app (executor removido/revogado) permanece terminal."""
    _msg, _tb, terminal = _classify_connection_error(_conn_closed(code))
    assert terminal is True, f"close code {code} deve ser terminal"


@pytest.mark.parametrize("code", [1006, 1001, 1011, 4408])
def test_close_code_transitorio_nao_e_terminal(code):
    """Queda abrupta / going-away / heartbeat timeout → reconectar."""
    _msg, _tb, terminal = _classify_connection_error(_conn_closed(code))
    assert terminal is False, f"close code {code} nao deve ser terminal"


def test_oserror_de_rede_nao_e_terminal():
    _msg, _tb, terminal = _classify_connection_error(ConnectionRefusedError("recusado"))
    assert terminal is False
