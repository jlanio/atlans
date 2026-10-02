"""
`get_agent_http_config` (flow) decide se desliga TLS/mTLS pelo HOSTNAME exato.

Antes o flow comparava por substring (`"localhost" in base_url`): um servidor
`wss://localhost.evil.tld`, ou qualquer URL com "localhost" na query, virava
"local" e os nos (publish_map, send_email, response_node...) falavam com ele
com `verify=False`, sem mTLS. O executor ja tinha corrigido a mesma regra em
`executor.utils.is_local_server`; agora ha uma implementacao so, no flow/.
"""
from unittest.mock import patch

import pytest

from flow.utils import executor_http
from flow.utils.executor_http import get_agent_http_config, is_local_server

_CTX = object()


@pytest.mark.parametrize("url", [
    "wss://localhost.evil.tld",
    "wss://agents.example.com/ws?volta=localhost",
    "wss://127.0.0.1.nip.io",
    "https://evil.tld/host.docker.internal",
])
def test_host_que_so_contem_localhost_nao_desliga_mtls(url):
    with patch("executor.utils.build_mtls_ssl_context", return_value=_CTX):
        _, _, verify = get_agent_http_config(url)
    assert verify is _CTX


@pytest.mark.parametrize("url", [
    "ws://localhost:8000",
    "ws://LOCALHOST:8000",
    "ws://127.0.0.1:8000",
    "ws://[::1]:8000",
    "ws://host.docker.internal:8000",
])
def test_servidor_local_de_verdade_segue_sem_tls(url):
    base_url, headers, verify = get_agent_http_config(url)
    assert verify is False
    assert headers == {}
    assert base_url.startswith("http://")


def test_executor_reusa_a_mesma_regra():
    from executor import utils as executor_utils

    assert executor_utils.is_local_server is is_local_server
    assert executor_http._LOCAL_HOSTS == frozenset(
        {"localhost", "127.0.0.1", "::1", "host.docker.internal"}
    )


def test_url_malformada_nao_e_local():
    assert is_local_server("ws://[::1") is False
