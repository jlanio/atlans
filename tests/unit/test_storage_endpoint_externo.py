# tests/unit/test_storage_endpoint_externo.py
"""
`endpoint_externo_e_local` — o critério do aviso de boot sobre `MINIO_EXTERNAL_ENDPOINT`.

O default do compose (`http://localhost:9000`) gera URLs pré-assinadas que só
abrem na máquina do servidor; em produção isso aparece como link quebrado no
Drive, nos artefatos e no MCP, sem nenhum erro no log. O lifespan avisa quando
o host é local. Aqui só a função: o lifespan sobe Redis, consumer e scheduler,
e não é o que está em jogo.
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
    "http://MINIO:9000",          # host é case-insensitive
    "minio:9000",                 # sem scheme: o host ainda é "minio", não o scheme
    "",                           # sem endpoint não há URL que preste
    "   ",
])
def test_hosts_locais_ou_vazio_contam_como_local(monkeypatch, endpoint):
    monkeypatch.setattr(storage, "_EXTERNAL_ENDPOINT", endpoint)
    assert storage.endpoint_externo_e_local() is True


@pytest.mark.parametrize("endpoint", [
    "https://s3.atlans.example.org",
    "https://s3.atlans.example.org:443/",
    "http://10.0.0.5:9000",       # IP privado mas alcançável por executores na mesma rede: não é "local"
    "http://minio.interno.exemplo:9000",
    "http://localhost.exemplo.com",  # só o host inteiro conta, não o prefixo
])
def test_hosts_externos_nao_sao_locais(monkeypatch, endpoint):
    monkeypatch.setattr(storage, "_EXTERNAL_ENDPOINT", endpoint)
    assert storage.endpoint_externo_e_local() is False


def test_le_o_valor_no_momento_da_chamada(monkeypatch):
    """O módulo resolve o endpoint no import; a função tem de olhar o valor
    atual, senão o aviso reflete o ambiente de quando o processo importou."""
    monkeypatch.setattr(storage, "_EXTERNAL_ENDPOINT", "http://localhost:9000")
    assert storage.endpoint_externo_e_local() is True
    monkeypatch.setattr(storage, "_EXTERNAL_ENDPOINT", "https://s3.atlans.example.org")
    assert storage.endpoint_externo_e_local() is False
