"""
The logger redacts personal access tokens (atl_pat_...) — bare and behind Bearer.

A forgotten `logger.info("token %s", segredo)` must not turn into a secret in a
log file. The pattern covers the exact format (prefix + 43 url-safe chars);
similar but shorter prefixes are not touched, so as not to redact ordinary text.
"""
import logging

from app.core.utils.logger import _scrub, get_logger

SEGREDO = "atl_pat_" + "Ab3dEf7gH1jK2lM4nO5pQ6rS8tU9vW0xY_Z-abcdefg"  # pragma: allowlist secret
assert len(SEGREDO) == 8 + 43


def test_scrub_redacts_bare_token_and_bearer():
    saida = _scrub(f"criado {SEGREDO} para ana; Authorization: Bearer {SEGREDO}")
    assert SEGREDO not in saida
    assert saida.count("<REDACTED>") == 2


def test_scrub_redacts_token_glued_to_another_word():
    """`id=atl_pat_…`, `_atl_pat_…`: no word boundary before the prefix."""
    saida = _scrub(f"chave=x{SEGREDO} e _{SEGREDO} e ({SEGREDO})")
    assert SEGREDO not in saida
    assert saida.count("<REDACTED>") == 3


def test_scrub_does_not_touch_short_prefix_or_plain_text():
    texto = "o prefixo exibido é atl_pat_Ab3d e a doc fala de atl_pat_ em geral"
    assert _scrub(texto) == texto


def test_app_logger_redacts_in_record(caplog):
    logger = get_logger("teste.pat")
    with caplog.at_level(logging.INFO, logger="teste.pat"):
        logger.info("Token novo: %s", SEGREDO)
        logger.info(f"interpolado {SEGREDO}")
    registrado = " ".join(r.getMessage() for r in caplog.records)
    assert SEGREDO not in registrado
    assert "<REDACTED>" in registrado
