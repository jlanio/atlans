"""O log de instanciação da fábrica não pode imprimir credencial em claro.

O servidor resolve a credencial e injeta o valor DECIFRADO nas properties do nó
antes de instanciá-lo. O `logger.debug` da fábrica imprimia essas properties
inteiras — em DEBUG, o token Bearer e a senha do banco do usuário ficavam em
texto puro no arquivo de log e em qualquer coletor para onde ele fosse enviado.
"""
import logging


from flow.factory import NodeFactory, _sem_segredos


def test_valores_sensiveis_viram_marcador():
    limpo = _sem_segredos({
        "url": "https://api.exemplo.com/x",
        "http_auth": {"type": "http_bearer", "token": "SEGREDO"},
        # Valor de mentira, com a forma do real de propósito: é essa forma que
        # o redator tem de reconhecer.
        "connectionString": "postgresql://u:senha@host/db",  # pragma: allowlist secret
        "method": "GET",
    })
    assert limpo["http_auth"] == "***"
    assert limpo["connectionString"] == "***"
    # O que não é segredo continua legível — o log existe para depurar.
    assert limpo["url"] == "https://api.exemplo.com/x"
    assert limpo["method"] == "GET"


def test_comparacao_de_nome_ignora_caixa():
    assert _sem_segredos({"Token": "abc", "PASSWORD": "x"}) == {"Token": "***", "PASSWORD": "***"}


def test_o_segredo_nao_aparece_no_log_da_fabrica(caplog):
    fabrica = NodeFactory()
    node_def = {
        "id": "n1",
        "name": "HttpRequest",
        "properties": {
            "url": "https://api.exemplo.com/x",
            "method": "GET",
            "http_auth": {"type": "http_bearer", "token": "TOKEN-DO-USUARIO"},
        },
    }
    with caplog.at_level(logging.DEBUG):
        fabrica.create(node_def)

    assert "TOKEN-DO-USUARIO" not in caplog.text
    # A linha continua útil: nó, id e os parâmetros não sensíveis.
    assert "HttpRequest" in caplog.text
    assert "https://api.exemplo.com/x" in caplog.text
