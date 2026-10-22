"""
Download to a file (flow/utils/download_seguro.py) — DataInput's URL origin.

What it must hold: the body goes to disk with a size limit that stops the
download, every redirect hop is revalidated against SSRF, the token does not
follow a hop to another origin, and only what is transient is retried.
"""
import os
import ssl

import httpx
import pytest

from flow.utils import circuit_breaker
from flow.utils.download_seguro import (
    MAX_REDIRECTS,
    baixar_para_arquivo,
    nome_sugerido,
    para_registro,
)
from tests.unit._rede_falsa import RedeFalsa

URL = "https://dados.exemplo.gov.br/arquivos/municipios.csv"


@pytest.fixture
def rede(monkeypatch, tmp_path):
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    return RedeFalsa().instalar(monkeypatch)


def _sobras(tmp_path):
    return [n for n in os.listdir(tmp_path) if n.startswith("atlans-download-")]


async def test_writes_the_body_to_a_file_through_the_pinned_ip(rede, tmp_path):
    rede.rota(URL, httpx.Response(200, content=b"a;b\n1;2\n", headers={"ETag": '"v1"'}))

    baixado = await baixar_para_arquivo(URL)

    with open(baixado.caminho, "rb") as f:
        assert f.read() == b"a;b\n1;2\n"
    assert baixado.tamanho == 8 and baixado.inicio == b"a;b\n1;2\n"
    assert baixado.status == 200 and baixado.url_final == URL
    assert baixado.headers["etag"] == '"v1"'
    pedido = rede.pedidos[0]
    # The connection goes to the IP validated, the name only in `Host`.
    assert pedido.url.host == "200.10.0.1"
    assert pedido.headers["host"] == "dados.exemplo.gov.br"
    assert pedido.headers["user-agent"].startswith("Atlans/entrada-de-dados")
    os.unlink(baixado.caminho)


async def test_declared_size_above_the_limit_is_refused_before_reading(rede, tmp_path):
    lidos = []

    async def corpo():
        lidos.append(1)
        yield b"x" * 1024

    rede.rota(URL, lambda _p: httpx.Response(200, headers={"Content-Length": str(50 * 1024 ** 2)}, content=corpo()))

    with pytest.raises(ValueError, match="tamanho máximo do download, 10 MB"):
        await baixar_para_arquivo(URL, max_bytes=10 * 1024 ** 2)
    assert lidos == []
    assert _sobras(tmp_path) == []


async def test_undeclared_size_stops_the_download_at_the_limit(rede, tmp_path):
    enviados = []

    async def corpo():
        for _ in range(100):
            enviados.append(1)
            yield b"x" * 64 * 1024

    rede.rota(URL, lambda _p: httpx.Response(200, content=corpo()))

    with pytest.raises(ValueError, match="tamanho máximo do download"):
        await baixar_para_arquivo(URL, max_bytes=100_000)
    # The body is written in 1 MiB chunks, so the download stops within one
    # chunk of the limit — far from the 6.4 MB the server would send.
    assert len(enviados) <= 17
    assert _sobras(tmp_path) == []


async def test_the_size_refusal_does_not_open_the_hosts_circuit(rede):
    rede.rota(URL, httpx.Response(200, content=b"x" * 2048))

    for _ in range(6):
        with pytest.raises(ValueError):
            await baixar_para_arquivo(URL, max_bytes=1024)

    assert circuit_breaker.get_circuit_breaker("http:dados.exemplo.gov.br").state == "closed"


async def test_follows_a_relative_redirect(rede):
    rede.rota(URL, httpx.Response(302, headers={"Location": "/storage/municipios.csv?sig=abc"}))
    rede.rota("https://dados.exemplo.gov.br/storage/municipios.csv", httpx.Response(200, content=b"ok"))

    baixado = await baixar_para_arquivo(URL)

    assert baixado.url_final == "https://dados.exemplo.gov.br/storage/municipios.csv?sig=abc"
    # The query of the Location (the temporary signature) reached the server.
    assert rede.pedidos[1].url.query == b"sig=abc"
    os.unlink(baixado.caminho)


async def test_a_redirect_to_an_internal_address_is_refused(rede):
    rede.rota(URL, httpx.Response(302, headers={"Location": "http://interno.exemplo/latest/meta-data/"}))

    with pytest.raises(ValueError, match="internos/privados"):
        await baixar_para_arquivo(URL)
    assert len(rede.pedidos) == 1


async def test_a_redirect_to_a_literal_internal_ip_is_refused(rede):
    rede.rota(URL, httpx.Response(301, headers={"Location": "http://169.254.169.254/"}))

    with pytest.raises(ValueError, match="internos/privados"):
        await baixar_para_arquivo(URL)


async def test_stops_after_the_redirect_limit(rede):
    rede.rota(URL, lambda p: httpx.Response(302, headers={"Location": URL}))

    with pytest.raises(RuntimeError, match=f"Limite de {MAX_REDIRECTS} redirecionamentos"):
        await baixar_para_arquivo(URL)
    assert len(rede.pedidos) == MAX_REDIRECTS + 1


async def test_the_token_follows_only_a_same_origin_redirect(rede):
    rede.rota(URL, httpx.Response(302, headers={"Location": "/v2/municipios.csv"}))
    rede.rota(
        "https://dados.exemplo.gov.br/v2/municipios.csv",
        httpx.Response(302, headers={"Location": "https://cdn.exemplo.net/m.csv"}),
    )
    rede.rota("https://cdn.exemplo.net/m.csv", httpx.Response(200, content=b"ok"))

    baixado = await baixar_para_arquivo(URL, headers={"Authorization": "Bearer segredo"})

    assert [p.headers.get("authorization") for p in rede.pedidos] == ["Bearer segredo", "Bearer segredo", None]
    os.unlink(baixado.caminho)


async def test_a_client_error_fails_at_once_with_the_servers_answer(rede):
    rede.rota(URL, httpx.Response(404, text="<h1>Arquivo removido</h1>"))

    with pytest.raises(RuntimeError, match="HTTP 404") as erro:
        await baixar_para_arquivo(URL)
    assert "Arquivo removido" in str(erro.value)
    assert len(rede.pedidos) == 1


async def test_retries_an_overloaded_server(rede):
    respostas = iter([httpx.Response(503), httpx.Response(200, content=b"ok")])
    rede.rota(URL, lambda _p: next(respostas))

    baixado = await baixar_para_arquivo(URL)

    assert len(rede.pedidos) == 2
    os.unlink(baixado.caminho)


async def test_retries_a_network_failure_then_gives_up(rede):
    def cai(_pedido):
        raise httpx.ConnectError("conexão recusada")

    rede.rota(URL, cai)

    with pytest.raises(RuntimeError, match="Erro de rede no download"):
        await baixar_para_arquivo(URL, tentativas=2)
    assert len(rede.pedidos) == 3


def test_the_url_shown_hides_secrets():
    url = "https://user:senha@s3.exemplo.net/b/x.zip?X-Amz-Signature=abc123&X-Amz-Expires=60&token=t0k&ano=2024"  # pragma: allowlist secret

    mostrada = para_registro(url)

    assert "senha" not in mostrada and "abc123" not in mostrada and "t0k" not in mostrada
    assert "X-Amz-Expires=60" in mostrada and "ano=2024" in mostrada


def test_a_malformed_url_shown_still_hides_secrets():
    # A typo in the port used to make the masking give up and return the URL as typed.
    mostrada = para_registro("https://user:senha@dados.exemplo.gov.br:44x/a.zip?token=t0k")  # pragma: allowlist secret

    assert "senha" not in mostrada and "t0k" not in mostrada
    assert mostrada == "https://dados.exemplo.gov.br:44x/a.zip?token=***"
    assert para_registro("https://[::1/a?token=t0k") == "(URL inválida)"


async def test_a_full_disk_does_not_open_the_hosts_circuit(rede, monkeypatch):
    rede.rota(URL, httpx.Response(200, content=b"a;b\n1;2\n"))

    class _DiscoCheio:
        def write(self, _parte):
            raise OSError(28, "No space left on device")

        def flush(self):
            pass

        def close(self):
            pass

    def fdopen(fd, *_a, **_k):
        os.close(fd)
        return _DiscoCheio()

    monkeypatch.setattr(os, "fdopen", fdopen)

    for _ in range(6):
        with pytest.raises(RuntimeError, match="disco do executor"):
            await baixar_para_arquivo(URL)

    assert circuit_breaker.get_circuit_breaker("http:dados.exemplo.gov.br").state == "closed"


@pytest.mark.parametrize("escrita_falha", [True, False], ids=["write-and-close", "close-only"])
async def test_a_close_that_fails_is_still_the_disk(rede, monkeypatch, tmp_path, escrita_falha):
    # With the disk full, closing the file flushes its buffer and fails again:
    # after a failed write that error must not replace the write's, and alone
    # it is the disk's as well, not the host's.
    rede.rota(URL, httpx.Response(200, content=b"a;b\n1;2\n"))

    class _DiscoCheio:
        def write(self, _parte):
            if escrita_falha:
                raise OSError(28, "No space left on device")

        def flush(self):
            pass

        def close(self):
            raise OSError(28, "No space left on device")

    def fdopen(fd, *_a, **_k):
        os.close(fd)
        return _DiscoCheio()

    monkeypatch.setattr(os, "fdopen", fdopen)

    for _ in range(6):
        with pytest.raises(RuntimeError, match="disco do executor"):
            await baixar_para_arquivo(URL)

    assert circuit_breaker.get_circuit_breaker("http:dados.exemplo.gov.br").state == "closed"
    assert _sobras(tmp_path) == []


async def test_a_tls_error_in_the_middle_of_the_body_is_the_network(rede, tmp_path):
    # anyio raises a corrupted TLS record as a bare ssl.SSLError — an OSError —
    # instead of httpx's ReadError. It is retried like any network failure and
    # never reported as the executor's disk.
    async def corpo():
        yield b"a;b\n"
        raise ssl.SSLError(1, "[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC] decryption failed or bad record mac")

    rede.rota(URL, lambda _p: httpx.Response(200, content=corpo()))

    with pytest.raises(RuntimeError, match="Erro de rede no download") as erro:
        await baixar_para_arquivo(URL, tentativas=1)

    assert "BAD_RECORD_MAC" in str(erro.value) and "disco" not in str(erro.value)
    assert len(rede.pedidos) == 2
    assert _sobras(tmp_path) == []


@pytest.mark.parametrize(("valor", "esperado"), [
    ('attachment; filename="BR_Municipios_2022.zip"', "BR_Municipios_2022.zip"),
    ("attachment; filename*=UTF-8''munic%C3%ADpios.zip", "municípios.zip"),
    ('attachment; filename="../../etc/passwd"', "passwd"),
    ("inline", ""),
])
def test_suggested_name(valor, esperado):
    assert nome_sugerido({"content-disposition": valor}) == esperado
