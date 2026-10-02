# tests/unit/test_sync_delete_idempotente.py
"""
Remocao no Drive pelo executor: rota mTLS correta + 404 idempotente.

Sintoma real, colhido do log de um executor em uso:

    SYNC  Falha ao remover f4ee8c0b-...: HTTP 404
    SYNC  Sync 'teste_imoveld - copia (24)': falhou (tentativa 9) —
          proximo retry em 256s.

O 404 NAO era "o arquivo ja foi apagado". Era a delecao apontando para o
endpoint errado: `DELETE /drive/{id}` exige JWT (o executor so tem mTLS) e, no
host `agents.atlans.example.org`, o Traefik roteia para a API apenas `/drive/executor-*`
(compose: `executores-rest.rule`). Um `/drive/{id}` cru morria no Traefik com
404 — o pedido nem chegava ao backend, e o WorkspaceFile continuava listado na
UI mesmo apos F5.

Duas coisas fecham o caso, e este arquivo tranca as duas:

  * a delecao vai para `/drive/executor-file/{id}` (rota mTLS de executor);
  * 404 continua contando como sucesso — no endpoint CERTO, ele significa que o
    registro ja nao existe (apagado pelo Drive web, ou por tentativa anterior).
    Tratar 404 como falha criava um retry que nunca converge, e ao esgotar as
    tentativas o dataset saia da fila mas PERMANECIA no manifesto — o proximo
    `diff` o via de novo como removido e reenfileirava, para sempre.
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
    """Constroi um DriveUploader com o HTTP dublado por status."""
    from executor.sync import uploader as mod

    def montar(status):
        up = mod.DriveUploader.__new__(mod.DriveUploader)
        up.base_url = "https://servidor"
        up._httpx_kwargs = {}
        up._headers = lambda: {}
        # O uploader nao abre mais um AsyncClient por requisicao: ele pede o
        # cliente compartilhado a `self._http()`.
        cliente = _Client(status)
        up._http = lambda: cliente
        return up

    return montar


@pytest.mark.asyncio
async def test_delete_usa_a_rota_mtls_de_executor(uploader):
    """A remocao PRECISA ir para /drive/executor-* — o unico prefixo que o
    Traefik roteia para a API no host dos executores. Um /drive/{id} cru morre
    no Traefik com 404, e o 404-como-sucesso fazia o executor desistir com o
    arquivo ainda no Drive. Este teste tranca a rota contra um refactor que a
    devolvesse ao caminho quebrado."""
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
    """O caso do bug. Ja nao estar la e o mesmo que ter sido apagado — mesma
    politica do `allow_missing=True` que o servidor usa no `delete_strict`."""
    assert await uploader(404).delete("abc") is True


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [403, 409, 500, 502])
async def test_outros_erros_continuam_sendo_falha(uploader, status):
    """Idempotencia vale so para "nao existe". Um 500 e transitorio e merece
    retry; um 403 e problema de permissao que precisa aparecer."""
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
    """Sair so da fila deixava o dataset no manifesto. Como ele tambem ja nao
    esta no disco, o proximo `diff` o classificava de novo como removido
    localmente e reenfileirava — o ciclo recomecava do zero, indefinidamente."""
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
    """So o delete limpa o manifesto. Um upload que esgotou tentativas se refere
    a um arquivo que EXISTE no disco — apaga-lo do manifesto o faria voltar como
    "novo" e reiniciar o mesmo upload que ja falhou dez vezes."""
    from executor.sync.queue import SyncQueue, _MAX_RETRIES

    manifesto = _Manifesto([
        {"action": "upload", "dataset": "ds2", "retries": _MAX_RETRIES},
    ])

    async def _nunca_chamado(item):
        raise AssertionError("nao deveria tentar de novo apos esgotar")

    await SyncQueue(manifesto, _nunca_chamado).process_pending()

    assert manifesto.desenfileirados == ["ds2"]
    assert manifesto.removidos == []
