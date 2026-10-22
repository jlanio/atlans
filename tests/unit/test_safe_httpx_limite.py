"""
`max_response_bytes` of `safe_httpx_request` limits what is READ, not what was
already read.

Before, the limit was compared after `aread()`: a 2 GB answer went whole into
the executor's memory only to be refused. HttpRequest's "Tamanho máximo da
resposta (MB)" promised to stop the read and did not.
"""
import httpx
import pytest

from flow.utils.geo_helpers import safe_httpx_request
from tests.unit._rede_falsa import RedeFalsa

URL = "https://dados.exemplo.gov.br/api/itens"


@pytest.fixture
def rede(monkeypatch):
    return RedeFalsa().instalar(monkeypatch)


async def test_stops_reading_at_the_limit(rede):
    enviados = []

    async def corpo():
        for _ in range(100):
            enviados.append(1)
            yield b"x" * 1024

    rede.rota(URL, lambda _p: httpx.Response(200, content=corpo()))

    with pytest.raises(ValueError, match="excedeu o limite de 4096 bytes"):
        await safe_httpx_request("GET", URL, max_response_bytes=4096)
    assert len(enviados) <= 5


async def test_a_declared_size_above_the_limit_is_refused_unread(rede):
    lidos = []

    async def corpo():
        lidos.append(1)
        yield b"{}"

    rede.rota(URL, lambda _p: httpx.Response(200, headers={"Content-Length": "999999"}, content=corpo()))

    with pytest.raises(ValueError, match="excedeu o limite"):
        await safe_httpx_request("GET", URL, max_response_bytes=1000)
    assert lidos == []


@pytest.mark.parametrize(("metodo", "status"), [("HEAD", 200), ("GET", 304)])
async def test_a_bodiless_answer_is_not_refused_by_its_content_length(rede, metodo, status):
    # HEAD and 304 carry the Content-Length of the resource, with no body: HttpRequest's
    # HEAD on a 100 MB file (to read its size or Last-Modified) used to pass, and must.
    rede.rota(URL, lambda _p: httpx.Response(status, headers={"Content-Length": str(100 * 1024 ** 2)}))

    resposta = await safe_httpx_request(metodo, URL, max_response_bytes=1000)

    assert resposta.status_code == status and resposta.content == b""


async def test_within_the_limit_the_response_reads_as_usual(rede):
    rede.rota(URL, httpx.Response(200, json={"itens": [1, 2]}))

    resposta = await safe_httpx_request("GET", URL, max_response_bytes=1000)

    assert resposta.json() == {"itens": [1, 2]}
    assert resposta.text == '{"itens":[1,2]}'


async def test_without_a_limit_nothing_changes(rede):
    rede.rota(URL, httpx.Response(200, content=b"x" * 5000))

    resposta = await safe_httpx_request("GET", URL)

    assert len(resposta.content) == 5000
