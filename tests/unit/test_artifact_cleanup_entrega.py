# tests/unit/test_artifact_cleanup_entrega.py
"""
The database row only goes away once the removal order WAS DELIVERED.

A local artifact lives on the executor's disk; the server only keeps the catalog.
Deleting the row without the executor having received the order leaves the file
orphaned: expired personal data, retained indefinitely, and with NOTHING in the
system recording that it exists. For LGPD that is the worst outcome — worse than
not having deleted it, because nobody can even know there is something to delete.

The bug these tests lock down was subtle: `_ordenar_remocao_local` wrapped the
send in a `try/except`, but `executor_registry.send_json` **returns False without
raising** when the executor is offline (and when the Redis relay has no listener,
and when the Ed25519 signature fails). The `except` covered only the rare case
and let the common case through — executor turned off — treating the order as
delivered.
"""
import pytest

from app.core import artifact_cleanup


def _items(n=2):
    return {
        "exec-1": [
            {"id_hash": f"h{i}", "local_path": f"a/{i}.gpkg", "_id": 100 + i}
            for i in range(n)
        ]
    }


class _Registry:
    """Doubles `executor_registry.send_json` with the return value the test wants."""

    def __init__(self, retorno):
        self.retorno = retorno
        self.enviados = []

    async def send_json(self, executor_id, data):
        self.enviados.append((executor_id, data))
        if isinstance(self.retorno, Exception):
            raise self.retorno
        return self.retorno


@pytest.fixture
def registry(monkeypatch):
    def instalar(retorno):
        r = _Registry(retorno)
        import app.core.executor_connections as ec
        monkeypatch.setattr(ec, "executor_registry", r, raising=False)
        return r
    return instalar


@pytest.mark.asyncio
async def test_confirmed_delivery_releases_the_db_row(registry):
    registry(True)
    entregues = await artifact_cleanup._ordenar_remocao_local(_items())
    assert entregues == [100, 101]


@pytest.mark.asyncio
async def test_OFFLINE_executor_does_not_release_the_row(registry):
    # The bug case: send_json returns False, with no exception. Before, the ids were
    # treated as delivered and the row was deleted — an orphaned file on disk.
    registry(False)
    entregues = await artifact_cleanup._ordenar_remocao_local(_items())
    assert entregues == [], (
        "ordem NAO entregue nao pode liberar a remocao da linha: o arquivo "
        "continua no disco do executor e a linha e o unico rastro dele"
    )


@pytest.mark.asyncio
async def test_exception_on_send_also_does_not_release(registry):
    registry(RuntimeError("websocket fechado"))
    assert await artifact_cleanup._ordenar_remocao_local(_items()) == []


@pytest.mark.asyncio
async def test_one_offline_executor_does_not_block_the_others(registry, monkeypatch):
    # Failure per executor, not per batch: one machine that is turned off must not
    # delay the retention of the others.
    class _Partial(_Registry):
        async def send_json(self, executor_id, data):
            self.enviados.append((executor_id, data))
            return executor_id != "exec-offline"

    import app.core.executor_connections as ec
    r = _Partial(None)
    # Via monkeypatch, so the double goes away at the end: assigned directly on the
    # module, it outlived the test and broke whoever used the registry afterwards
    # (the "now" block of the History metrics called `list_pending_acks` on it).
    monkeypatch.setattr(ec, "executor_registry", r)

    entregues = await artifact_cleanup._ordenar_remocao_local({
        "exec-offline": [{"id_hash": "a", "local_path": "x", "_id": 1}],
        "exec-online": [{"id_hash": "b", "local_path": "y", "_id": 2}],
    })
    assert entregues == [2]


@pytest.mark.asyncio
async def test_the_order_goes_as_signable_control(registry):
    # `purge_artifacts` must go out as `type: control` — that is what makes the
    # server sign it with Ed25519 (sign_if_needed) and the executor require it
    # signed. An unsigned order to delete files would be a data-destruction
    # channel for whoever won the connection.
    r = registry(True)
    await artifact_cleanup._ordenar_remocao_local(_items(1))

    _, msg = r.enviados[0]
    assert msg["type"] == "control"
    assert msg["action"] == "purge_artifacts"
    assert msg["artifacts"] == [{"id_hash": "h0", "local_path": "a/0.gpkg"}]
