"""
Error taxonomy (flow.utils.error_taxonomy): classifies the failure into a
stable category + derives retryable. It must look at the exception CHAIN,
because nodes wrap the original error in a RuntimeError (`raise ... from e`).
"""
import asyncio

import pytest

from flow.utils.error_taxonomy import classify_error, is_retryable


def _reraise_from(e: BaseException) -> RuntimeError:
    """Simulates the nodes' pattern: RuntimeError with the original cause chained."""
    try:
        raise RuntimeError("Erro na operação") from e
    except RuntimeError as re:
        return re


@pytest.mark.parametrize("exc, expected", [
    (MemoryError("Unable to allocate 11 GiB"), "resource"),
    (asyncio.TimeoutError(), "timeout"),
    (TimeoutError(), "timeout"),
    (ConnectionError("conn reset"), "transient"),
    (ValueError("coluna 'lat' não encontrada"), "user"),
    (TypeError("bad type"), "user"),
    (KeyError("missing"), "user"),
    (RuntimeError("algo inesperado"), "internal"),
])
def test_classifica_direto(exc, expected):
    assert classify_error(exc) == expected


@pytest.mark.parametrize("cause, expected", [
    (MemoryError(), "resource"),       # the OOM intersection case (RuntimeError <- MemoryError)
    (ValueError("coluna ausente"), "user"),
    (ConnectionError(), "transient"),
])
def test_classifica_pela_cadeia_quando_envolvido_em_runtimeerror(cause, expected):
    wrapped = _reraise_from(cause)
    assert isinstance(wrapped, RuntimeError)
    assert classify_error(wrapped) == expected


def test_retryable_derivado_da_categoria():
    assert is_retryable("timeout") is True
    assert is_retryable("transient") is True
    assert is_retryable("user") is False
    assert is_retryable("validation") is False
    assert is_retryable("resource") is False
    assert is_retryable("internal") is False
    assert is_retryable("desconhecida") is False
