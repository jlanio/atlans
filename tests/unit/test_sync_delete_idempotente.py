# tests/unit/test_sync_delete_idempotente.py
"""
Deletion in the Drive by the executor: correct mTLS route + idempotent 404.

Real symptom, taken from the log of an executor in use:

    SYNC  Falha ao remover f4ee8c0b-...: HTTP 404
    SYNC  Sync 'teste_imoveld - copia (24)': falhou (tentativa 9) —
          proximo retry em 256s.

The 404 was NOT "the file was already deleted". It was the deletion pointing at
the wrong endpoint: `DELETE /drive/{id}` requires a JWT (the executor only has
mTLS) and, on the `agents.atlans.example.org` host, Traefik routes only
`/drive/executor-*` to the API (compose: `executores-rest.rule`). A bare
`/drive/{id}` died at Traefik with a 404 — the request never even reached the
backend, and the WorkspaceFile stayed listed in the UI even after F5.

Two things close the case, and this file locks both down:

  * the deletion goes to `/drive/executor-file/{id}` (the executor mTLS route);
  * 404 still counts as success — on the RIGHT endpoint, it means the record
    no longer exists (deleted via the Drive web UI, or by an earlier attempt).
    Treating 404 as a failure created a retry that never converges, and once
    the attempts ran out the dataset left the queue but REMAINED in the
    manifest — the next `diff` saw it again as removed and re-enqueued it,
    forever.
"""
import pytest


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = ""


class _Client:
    """Dubla o cliente httpx de longa duracao guardado em `_http`."""

    def __init__(self, status):
        self._status = status
        self.ultimo_url: str | None = None

    async def delete(self, url, headers=None, timeout=None):
        self.ultimo_url = url
        return _Resp(self._status)


@pytest.fixture
def uploader():
    """Builds a DriveUploader with HTTP stubbed per status."""
    from executor.sync import uploader as mod

    def montar(status):
        up = mod.DriveUploader.__new__(mod.DriveUploader)
        up.base_url = "https://servidor"
        up._httpx_kwargs = {}
        up._headers = lambda: {}
        # The uploader no longer opens an AsyncClient per request: it asks
        # `self._http()` for the shared client.
        cliente = _Client(status)
        up._http = lambda: cliente
        return up

    return montar


@pytest.mark.asyncio
async def test_delete_usa_a_rota_mtls_de_executor(uploader):
    """The deletion MUST go to /drive/executor-* — the only prefix that Traefik
    routes to the API on the executors' host. A bare /drive/{id} dies at
    Traefik with a 404, and 404-as-success made the executor give up with the
    file still in the Drive. This test locks the route down against a refactor
    that would send it back to the broken path."""
    up = uploader(204)
    await up.delete("f4ee8c0b")
    url = up._http().ultimo_url
    assert url == "https://servidor/drive/executor-file/f4ee8c0b"
    assert "/drive/executor-" in url


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 204])
async def test_remocao_bem_sucedida(uploader, status):
    assert await uploader(status).delete("abc") is True


@pytest.mark.asyncio
async def test_404_conta_como_REMOVIDO(uploader):
    """The bug's case. No longer being there is the same as having been deleted —
    the same policy as the `allow_missing=True` the server uses in
    `delete_strict`."""
    assert await uploader(404).delete("abc") is True


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [403, 409, 500, 502])
async def test_outros_erros_continuam_sendo_falha(uploader, status):
    """Idempotency applies only to "does not exist". A 500 is transient and
    deserves a retry; a 403 is a permission problem that needs to surface."""
    assert await uploader(status).delete("abc") is False


# ── Desistir precisa significar parar de tentar ──────────────────────────────

class _Manifesto:
    def __init__(self, itens):
        self._itens = itens
        self.removidos: list[str] = []
        self.desenfileirados: list[str] = []

    def pending_items(self):
        return self._itens

    def dequeue(self, nome):
        self.desenfileirados.append(nome)

    def remove_dataset(self, nome):
        self.removidos.append(nome)

    def update_retry(self, nome, next_attempt_at=0.0):
        pass


@pytest.mark.asyncio
async def test_delete_esgotado_sai_do_MANIFESTO_tambem():
    """Leaving only the queue left the dataset in the manifest. Since it is also
    no longer on disk, the next `diff` classified it again as removed locally
    and re-enqueued it — the cycle started over from scratch, indefinitely."""
    from executor.sync.queue import SyncQueue, _MAX_RETRIES

    manifesto = _Manifesto([
        {"action": "delete", "dataset": "ds1", "retries": _MAX_RETRIES},
    ])

    async def _nunca_chamado(item):
        raise AssertionError("nao deveria tentar de novo apos esgotar")

    await SyncQueue(manifesto, _nunca_chamado).process_pending()

    assert manifesto.desenfileirados == ["ds1"]
    assert manifesto.removidos == ["ds1"], "sem isto o dataset volta na proxima varredura"


@pytest.mark.asyncio
async def test_upload_esgotado_NAO_some_do_manifesto():
    """Only the delete cleans the manifest. An upload that ran out of attempts
    refers to a file that EXISTS on disk — removing it from the manifest would
    bring it back as "new" and restart the same upload that already failed ten
    times."""
    from executor.sync.queue import SyncQueue, _MAX_RETRIES

    manifesto = _Manifesto([
        {"action": "upload", "dataset": "ds2", "retries": _MAX_RETRIES},
    ])

    async def _nunca_chamado(item):
        raise AssertionError("nao deveria tentar de novo apos esgotar")

    await SyncQueue(manifesto, _nunca_chamado).process_pending()

    assert manifesto.desenfileirados == ["ds2"]
    assert manifesto.removidos == []
