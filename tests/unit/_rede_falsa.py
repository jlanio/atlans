"""A fake internet for the nodes that download: DNS and HTTP, without network.

`RedeFalsa.instalar` answers `socket.getaddrinfo` with the IPs in `IPS` and
gives every `httpx.AsyncClient` an `httpx.MockTransport` that routes by the
`Host` header — the name the request was made to, since the download pins the
IP in the URL and keeps the name in `Host`
(flow/utils/geo_helpers.py::pin_request_target).
"""
import socket

import httpx

IPS = {
    "dados.exemplo.gov.br": "200.10.0.1",
    "cdn.exemplo.net": "200.20.0.2",
    "interno.exemplo": "10.0.0.7",
}


class RedeFalsa:
    def __init__(self):
        self.rotas = {}
        self.pedidos: list[httpx.Request] = []

    def rota(self, url: str, resposta=None):
        """Registers what `url` answers: an httpx.Response (the same every time)
        or a function `request -> httpx.Response`."""
        alvo = httpx.URL(url)
        chave = (alvo.host, alvo.path)
        if callable(resposta):
            self.rotas[chave] = resposta
        else:
            self.rotas[chave] = lambda _pedido: resposta

    def _despachar(self, request: httpx.Request) -> httpx.Response:
        self.pedidos.append(request)
        host = request.headers.get("host", "").split(":")[0]
        resposta = self.rotas.get((host, request.url.path))
        if resposta is None:
            return httpx.Response(404, text=f"sem rota para {host}{request.url.path}")
        return resposta(request)

    def instalar(self, monkeypatch) -> "RedeFalsa":
        def getaddrinfo(host, *args, **kwargs):
            ip = IPS.get(host)
            if ip is None:
                raise socket.gaierror(f"{host} desconhecido")
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

        monkeypatch.setattr("flow.utils.geo_helpers.socket.getaddrinfo", getaddrinfo)

        original = httpx.AsyncClient
        transporte = httpx.MockTransport(self._despachar)

        def cliente(*args, **kwargs):
            kwargs["transport"] = transporte
            return original(*args, **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", cliente)

        from flow.utils import circuit_breaker, download_seguro
        monkeypatch.setattr(circuit_breaker, "_registry", {})
        monkeypatch.setattr(download_seguro, "espera_exponencial", lambda *a, **k: 0)
        return self
