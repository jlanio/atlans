"""The factory's instantiation log must not print a credential in the clear.

The server resolves the credential and injects the DECRYPTED value into the
node's properties before instantiating it. The factory's `logger.debug` printed
those properties in full — in DEBUG, the user's Bearer token and database
password sat in plain text in the log file and in any collector it was shipped to.
"""
import logging


from flow.factory import NodeFactory, _sem_segredos


def test_valores_sensiveis_viram_marcador():
    limpo = _sem_segredos({
        "url": "https://api.exemplo.com/x",
        "http_auth": {"type": "http_bearer", "token": "SEGREDO"},
        # A fake value, shaped like the real one on purpose: that shape is what
        # the redactor has to recognize.
        "connectionString": "postgresql://u:senha@host/db",  # pragma: allowlist secret
        "method": "GET",
    })
    assert limpo["http_auth"] == "***"
    assert limpo["connectionString"] == "***"
    # What is not secret stays readable — the log exists for debugging.
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
    # The line stays useful: node, id and the non-sensitive parameters.
    assert "HttpRequest" in caplog.text
    assert "https://api.exemplo.com/x" in caplog.text
