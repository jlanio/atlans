"""
O logger redige tokens pessoais de acesso (atl_pat_...) — nus e atrás de Bearer.

Um `logger.info("token %s", segredo)` esquecido não pode virar segredo em
arquivo de log. O padrão cobre o formato exato (prefixo + 43 chars url-safe);
prefixos parecidos mas mais curtos não são tocados, para não redigir texto comum.
"""
import logging

from app.core.utils.logger import _scrub, get_logger

SEGREDO = "atl_pat_" + "Ab3dEf7gH1jK2lM4nO5pQ6rS8tU9vW0xY_Z-abcdefg"  # pragma: allowlist secret
assert len(SEGREDO) == 8 + 43


def test_scrub_redige_o_token_nu_e_o_bearer():
    saida = _scrub(f"criado {SEGREDO} para ana; Authorization: Bearer {SEGREDO}")
    assert SEGREDO not in saida
    assert saida.count("<REDACTED>") == 2


def test_scrub_redige_token_colado_a_outra_palavra():
    """`id=atl_pat_…`, `_atl_pat_…`: sem fronteira de palavra antes do prefixo."""
    saida = _scrub(f"chave=x{SEGREDO} e _{SEGREDO} e ({SEGREDO})")
    assert SEGREDO not in saida
    assert saida.count("<REDACTED>") == 3


def test_scrub_nao_toca_prefixo_curto_ou_texto_comum():
    texto = "o prefixo exibido é atl_pat_Ab3d e a doc fala de atl_pat_ em geral"
    assert _scrub(texto) == texto


def test_logger_da_app_redige_no_registro(caplog):
    logger = get_logger("teste.pat")
    with caplog.at_level(logging.INFO, logger="teste.pat"):
        logger.info("Token novo: %s", SEGREDO)
        logger.info(f"interpolado {SEGREDO}")
    registrado = " ".join(r.getMessage() for r in caplog.records)
    assert SEGREDO not in registrado
    assert "<REDACTED>" in registrado
