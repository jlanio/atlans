# executor/sync/http.py
"""
Cliente HTTP de longa duracao para os componentes do GeoSync.

Cada metodo do uploader/downloader abria um `async with httpx.AsyncClient(...)`
e o fechava ao sair do bloco. Como `mtls_httpx_kwargs` injeta o certificado de
cliente, isso significava um handshake mTLS COMPLETO por requisicao — e um
unico `_upload_file` abria tres (pedir URL, PUT no MinIO, confirmar). Numa rede
de campo com 150ms de latencia, um .geojson de 3 KB custava o mesmo tempo de
protocolo que um raster de 2 GB.
"""
import httpx

# Timeout das requisicoes de CONTROLE (pedir URL, confirmar, listar). Fica curto
# de proposito: sao chamadas pequenas e a falha precisa aparecer rapido.
TIMEOUT_CONTROLE = 30.0

# Timeout de LEITURA/ESCRITA das transferencias (PUT/GET de bytes no MinIO).
TIMEOUT_TRANSFERENCIA = 300.0


class ClienteHTTP:
    """Guarda um `httpx.AsyncClient` reaproveitavel, criado sob demanda.

    Preguicoso porque os componentes do sync sao construidos FORA do event loop
    (o main.py monta os SyncManagers antes de chamar `run()`): um AsyncClient
    criado ali nasceria amarrado ao loop errado.

    O timeout padrao ja cobre a transferencia; as chamadas de controle passam
    `timeout=TIMEOUT_CONTROLE` por requisicao.
    """

    def __init__(self, httpx_kwargs: dict):
        self._kwargs = httpx_kwargs
        self._cliente: httpx.AsyncClient | None = None

    def __call__(self) -> httpx.AsyncClient:
        if self._cliente is None or self._cliente.is_closed:
            self._cliente = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    TIMEOUT_CONTROLE,
                    read=TIMEOUT_TRANSFERENCIA,
                    write=TIMEOUT_TRANSFERENCIA,
                ),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
                **self._kwargs,
            )
        return self._cliente

    async def aclose(self) -> None:
        """Fecha o cliente. Um pool compartilhado precisa de fechamento
        explicito no shutdown, senao os sockets vazam ate o processo morrer."""
        if self._cliente is not None and not self._cliente.is_closed:
            await self._cliente.aclose()
        self._cliente = None
