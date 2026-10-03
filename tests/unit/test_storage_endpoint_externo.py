# tests/unit/test_storage_endpoint_externo.py
"""
`endpoint_externo_e_local` — the criterion for the boot warning about `MINIO_EXTERNAL_ENDPOINT`.

The compose default (`http://localhost:9000`) produces presigned URLs that only
open on the server machine; in production that shows up as a broken link in the
Drive, in artifacts and in MCP, with no error in the log. The lifespan warns when
the host is local. Only the function here: the lifespan starts Redis, the consumer
and the scheduler, and that is not what is at stake.
"""
from __future__ import annotations

import pytest

from app.core import storage


@pytest.mark.parametrize("endpoint", [
    "http://localhost:9000",
    "https://localhost",
    "http://127.0.0.1:9000",
    "http://[::1]:9000",
    "http://minio:9000",
    "http://MINIO:9000",          # host is case-insensitive
    "minio:9000",                 # no scheme: the host is still "minio", not the scheme
    "",                           # without an endpoint there is no usable URL
    "   ",
])
def test_hosts_locais_ou_vazio_contam_como_local(monkeypatch, endpoint):
    monkeypatch.setattr(storage, "_EXTERNAL_ENDPOINT", endpoint)
    assert storage.endpoint_externo_e_local() is True


@pytest.mark.parametrize("endpoint", [
    "https://s3.atlans.example.org",
    "https://s3.atlans.example.org:443/",
    "http://10.0.0.5:9000",       # private IP but reachable by executors on the same network: not "local"
    "http://minio.interno.exemplo:9000",
    "http://localhost.exemplo.com",  # only the whole host counts, not the prefix
])
def test_hosts_externos_nao_sao_locais(monkeypatch, endpoint):
    monkeypatch.setattr(storage, "_EXTERNAL_ENDPOINT", endpoint)
    assert storage.endpoint_externo_e_local() is False


def test_le_o_valor_no_momento_da_chamada(monkeypatch):
    """The module resolves the endpoint at import; the function has to look at the
    current value, otherwise the warning reflects the environment from when the process imported."""
    monkeypatch.setattr(storage, "_EXTERNAL_ENDPOINT", "http://localhost:9000")
    assert storage.endpoint_externo_e_local() is True
    monkeypatch.setattr(storage, "_EXTERNAL_ENDPOINT", "https://s3.atlans.example.org")
    assert storage.endpoint_externo_e_local() is False
