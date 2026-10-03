"""
Classification of executor connection errors (_classify_connection_error).

Regression: the executor treated HTTP 401/403/404 in the WS handshake as TERMINAL
(assumed "executor removed") and stopped reconnecting — exiting with exit 0,
which Docker's `restart: on-failure` does not restart. But the app NEVER denies
via HTTP status: every authoritative deny arrives as WS close code 4401/4403/4404.
An HTTP 4xx/5xx status in the handshake can only come from the EDGE
(Traefik/Cloudflare) and, during a deploy, it is transient (proxy without a
route / backend starting up).

Contract now:
  - InvalidStatus (any HTTP status)           -> NOT terminal (retry with backoff)
  - ConnectionClosed with code 4401/4403/4404 -> terminal (real deny from the app)
  - ConnectionClosed with code 1006/1001/...  -> NOT terminal (transient drop)
  - OSError (connection refused, DNS)         -> NOT terminal
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
def test_http_status_in_handshake_is_never_terminal(status):
    """The bug: a 404 from Traefik during a deploy must not bring the executor down."""
    _msg, _tb, terminal = _classify_connection_error(_invalid_status(status))
    assert terminal is False, f"HTTP {status} no handshake NAO deve ser terminal"


@pytest.mark.parametrize("code", [4401, 4403, 4404])
def test_close_code_4xxx_do_app_e_terminal(code):
    """Deny autoritativo do app (executor removido/revogado) permanece terminal."""
    _msg, _tb, terminal = _classify_connection_error(_conn_closed(code))
    assert terminal is True, f"close code {code} deve ser terminal"


@pytest.mark.parametrize("code", [1006, 1001, 1011, 4408])
def test_transient_close_code_is_not_terminal(code):
    """Queda abrupta / going-away / heartbeat timeout → reconectar."""
    _msg, _tb, terminal = _classify_connection_error(_conn_closed(code))
    assert terminal is False, f"close code {code} nao deve ser terminal"


def test_network_oserror_is_not_terminal():
    _msg, _tb, terminal = _classify_connection_error(ConnectionRefusedError("recusado"))
    assert terminal is False
