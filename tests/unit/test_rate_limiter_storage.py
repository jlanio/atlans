# tests/unit/test_rate_limiter_storage.py
"""
Storage do rate limiter: Redis compartilhado por padrao, memoria como saida.

Com contadores em memoria, `uvicorn --workers 4` da a cada worker o proprio
balde e um `10/minute` vale ate 4x. Por isso, sem configuracao, o limiter usa o
`REDIS_URL` da aplicacao; `RATE_LIMIT_STORAGE_URI` escolhe outro storage e
`memory://` volta para a memoria por worker. Aqui se verifica a fiacao da
fabrica — o `limits` constroi o RedisStorage sem conectar — e o prazo das idas
ao Redis contra um servidor que aceita a conexao e nunca responde.

O `limiter` global do modulo nao e tocado: os testes constroem instancias
novas por `criar_limiter()`. O conftest fixa `RATE_LIMIT_STORAGE_URI=memory://`
para a suite; cada teste aqui define as duas variaveis que importam.
"""
import logging
import socket
import threading
import time

import pytest

from app.core import rate_limiter


@pytest.fixture
def ambiente(monkeypatch):
    """Parte de nenhuma das duas variaveis definida."""
    monkeypatch.delenv("RATE_LIMIT_STORAGE_URI", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    return monkeypatch


def _kwargs_da_conexao(lim):
    return lim._storage.storage.connection_pool.connection_kwargs


def test_sem_nada_usa_memoria_e_nao_liga_fallback(ambiente):
    lim = rate_limiter.criar_limiter()
    assert type(lim._storage).__name__ == "MemoryStorage"
    assert lim._in_memory_fallback_enabled is False


def test_redis_url_vira_o_padrao_com_fallback_e_prazo(ambiente):
    """O caso de producao: o compose define REDIS_URL e deixa a outra vazia."""
    ambiente.setenv("RATE_LIMIT_STORAGE_URI", "")
    ambiente.setenv("REDIS_URL", "redis://:segredo@127.0.0.1:1/0")
    lim = rate_limiter.criar_limiter()
    assert type(lim._storage).__name__ == "RedisStorage"
    assert lim._in_memory_fallback_enabled is True
    assert type(lim._fallback_storage).__name__ == "MemoryStorage"
    kwargs = _kwargs_da_conexao(lim)
    assert (kwargs["socket_timeout"], kwargs["socket_connect_timeout"]) == (0.25, 0.25)


def test_memory_explicito_e_a_saida_mesmo_com_redis(ambiente):
    ambiente.setenv("RATE_LIMIT_STORAGE_URI", "memory://")
    ambiente.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    lim = rate_limiter.criar_limiter()
    assert type(lim._storage).__name__ == "MemoryStorage"
    assert lim._in_memory_fallback_enabled is False


def test_uri_explicita_vence_o_redis_url_e_a_query_vence_o_prazo(ambiente):
    ambiente.setenv("RATE_LIMIT_STORAGE_URI", "redis://127.0.0.1:2/3?socket_timeout=5")
    ambiente.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    lim = rate_limiter.criar_limiter()
    kwargs = _kwargs_da_conexao(lim)
    assert (kwargs["port"], kwargs["db"]) == (2, 3)
    assert kwargs["socket_timeout"] == 5.0           # a query da URI manda
    assert kwargs["socket_connect_timeout"] == 0.25  # o resto fica com o padrao


def test_redis_url_que_o_limits_nao_conhece_cai_para_memoria(ambiente, caplog):
    """`unix://` vale para o redis-py, mas o `limits` recusaria o esquema na
    importacao do modulo — a API nem subiria por causa de um padrao."""
    ambiente.setenv("REDIS_URL", "unix:///var/run/redis.sock")
    with caplog.at_level(logging.WARNING, logger=rate_limiter.logger.name):
        lim = rate_limiter.criar_limiter()
    assert type(lim._storage).__name__ == "MemoryStorage"
    assert "'unix'" in caplog.text


def test_log_de_arranque_diz_onde_ficam_os_contadores_sem_a_senha(ambiente, caplog):
    ambiente.setenv("REDIS_URL", "redis://:segredo-do-redis@redis:6379/0")
    with caplog.at_level(logging.INFO, logger=rate_limiter.logger.name):
        rate_limiter.criar_limiter()
    assert "redis://redis:6379/0" in caplog.text
    assert "segredo-do-redis" not in caplog.text


def test_log_de_arranque_nao_vaza_senha_com_barra(ambiente, caplog):
    """Uma `/` na senha faz o urlsplit empurrar o resto dela para o caminho."""
    ambiente.setenv("REDIS_URL", "redis://:S3CR3T/cauda-secreta@redis:6379/0")
    with caplog.at_level(logging.INFO, logger=rate_limiter.logger.name):
        rate_limiter.criar_limiter()
    assert "S3CR3T" not in caplog.text
    assert "cauda-secreta" not in caplog.text


@pytest.mark.parametrize("variavel, valor", [
    ("RATE_LIMIT_STORAGE_URI", "memory"),                       # typo da saida de emergencia
    ("RATE_LIMIT_STORAGE_URI", "rediss+nada://redis:6379/0"),   # esquema que o limits nao conhece
    ("REDIS_URL", "REDIS://redis:6379/0"),                      # o redis-py nao aceita maiusculas
    ("REDIS_URL", "redis://:a[b]c@redis:6379/0"),               # urlsplit: "Invalid IPv6 URL"
    ("REDIS_URL", "redis://redis:porta/0"),                     # porta nao numerica
])
def test_uri_invalida_cai_em_memoria_sem_derrubar_a_importacao(ambiente, caplog, variavel, valor):
    """A fabrica roda na importacao do modulo: uma excecao aqui derrubava os
    quatro workers por causa de uma variavel de rate limit."""
    ambiente.setenv(variavel, valor)
    with caplog.at_level(logging.INFO, logger=rate_limiter.logger.name):
        lim = rate_limiter.criar_limiter()
    assert type(lim._storage).__name__ == "MemoryStorage"
    assert lim._in_memory_fallback_enabled is False
    assert "memoria de cada worker" in caplog.text


def test_socket_unix_tambem_ganha_o_prazo(ambiente):
    ambiente.setenv("RATE_LIMIT_STORAGE_URI", "redis+unix:///var/run/redis.sock")
    lim = rate_limiter.criar_limiter()
    kwargs = _kwargs_da_conexao(lim)
    assert (kwargs["socket_timeout"], kwargs["socket_connect_timeout"]) == (0.25, 0.25)


def test_a_suite_conta_em_memoria():
    """O conftest fixa memory:// para o limiter global, mesmo com um
    RATE_LIMIT_STORAGE_URI de dev apontando para um Redis de verdade."""
    assert type(rate_limiter.limiter._storage).__name__ == "MemoryStorage"


def test_log_de_arranque_avisa_quando_e_memoria(ambiente, caplog):
    with caplog.at_level(logging.INFO, logger=rate_limiter.logger.name):
        rate_limiter.criar_limiter()
    assert "memoria de cada worker" in caplog.text


def test_redis_travado_nao_prende_o_worker(ambiente):
    """Um Redis que aceita a conexao e nao responde. Sem prazo, a conferencia
    do slowapi (e cada `hit`) fica presa no event loop sem fim."""
    servidor = socket.socket()
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(8)
    aceitas = []
    threading.Thread(target=lambda: aceitas.append(servidor.accept()), daemon=True).start()
    try:
        ambiente.setenv("REDIS_URL", f"redis://127.0.0.1:{servidor.getsockname()[1]}/0")
        lim = rate_limiter.criar_limiter()
        resultado = []
        inicio = time.monotonic()
        conferencia = threading.Thread(target=lambda: resultado.append(lim._storage.check()), daemon=True)
        conferencia.start()
        conferencia.join(10)
        assert not conferencia.is_alive(), "a conferencia ficou presa no Redis travado"
        assert resultado == [False]
        assert time.monotonic() - inicio < 5
    finally:
        servidor.close()
        for conexao, _ in aceitas:
            conexao.close()


def test_redis_fora_do_ar_cai_para_memoria_e_o_limite_segue_valendo(ambiente):
    """Pela rota, como em producao: a API nao cai com o Redis e o limite da
    rota continua contado — em memoria, ate o Redis voltar."""
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    ambiente.setenv("REDIS_URL", "redis://127.0.0.1:1/0")      # porta 1: conexao recusada
    lim = rate_limiter.criar_limiter()
    app = FastAPI()
    app.state.limiter = lim
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/limitada")
    @lim.limit("2/minute")
    async def limitada(request: Request):
        return {"ok": True}

    with TestClient(app) as cliente:
        codigos = [cliente.get("/limitada").status_code for _ in range(3)]

    assert codigos == [200, 200, 429]
    assert lim._storage_dead is True


def test_limiter_global_continua_usando_a_chave_por_ip_real():
    """A fabrica nao pode ter trocado a key_func: sem ela volta o balde unico do proxy."""
    assert rate_limiter.limiter._key_func is rate_limiter._client_key
