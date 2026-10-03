"""Default secret redaction also applies in the executor and in flow.

The list (DSN with password, Bearer, Basic, PAT...) lived in `app/core/utils/logger`
and only the app's loggers used it: the executor, which decrypts DSNs and builds
authentication headers, logged everything unmasked. Now it lives in flow/, the app
re-exports it, and the executor hooks it into the LogRecord factory.
"""
import io
import logging

import pytest

from flow.utils import redacao_log

DSN = "postgresql://leitor:SenhaForte123@db.interno:5432/geo"  # pragma: allowlist secret
BEARER = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.assinaturaassinatura"  # pragma: allowlist secret


@pytest.fixture
def isolated_factory():
    fabrica, instalada = logging.getLogRecordFactory(), redacao_log._installed
    redacao_log._installed = False
    yield
    logging.setLogRecordFactory(fabrica)
    redacao_log._installed = instalada


def _capture(nome: str):
    fluxo = io.StringIO()
    handler = logging.StreamHandler(fluxo)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger(nome)
    logger.handlers[:] = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger, fluxo


def test_app_reexports_the_same_list():
    from app.core.utils import logger as app_logger

    assert app_logger.scrub_text is redacao_log.scrub_text
    assert app_logger._SCRUB_PATTERNS is redacao_log._SCRUB_PATTERNS


def test_factory_redacts_third_party_logger_without_filter(isolated_factory):
    """The third-party handler/logger has no filter at all: the factory is what catches it."""
    redacao_log.install_in_process()
    logger, fluxo = _capture("asyncpg.terceiro")
    logger.error("falhou em %s com %s", DSN, BEARER)
    saida = fluxo.getvalue()
    assert "SenhaForte123" not in saida and "assinaturaassinatura" not in saida
    assert "db.interno" in saida  # the diagnostic is still useful


def test_non_string_argument_is_also_redacted(isolated_factory):
    """The driver exception carries the DSN in its `str()` — `%s` of an object."""
    redacao_log.install_in_process()
    logger, fluxo = _capture("executor.teste_objeto")
    logger.error("conexão recusada: %s", ConnectionError(f"não conectou em {DSN}"))
    assert "SenhaForte123" not in fluxo.getvalue()


def test_traceback_is_redacted(isolated_factory):
    redacao_log.install_in_process()
    logger, fluxo = _capture("executor.teste_traceback")
    try:
        raise RuntimeError(f"erro com {DSN}")
    except RuntimeError:
        logger.exception("falha no nó")
    assert "SenhaForte123" not in fluxo.getvalue()
    assert "RuntimeError" in fluxo.getvalue()


def test_record_without_secret_keeps_its_shape(isolated_factory):
    """Some formatters read `record.args` (uvicorn's access one)."""
    redacao_log.install_in_process()
    registro = logging.getLogger("x").makeRecord("x", logging.INFO, __file__, 1, "%s %s", ("a", "b"), None)
    assert registro.args == ("a", "b")


def test_install_is_idempotent(isolated_factory):
    redacao_log.install_in_process()
    primeira = logging.getLogRecordFactory()
    redacao_log.install_in_process()
    assert logging.getLogRecordFactory() is primeira


def test_executor_configure_logging_enables_redaction(isolated_factory, monkeypatch):
    from executor import logging_setup

    root = logging.getLogger()
    originais, nivel = list(root.handlers), root.level
    estado = (logging_setup._console, logging_setup._configured)
    logging_setup._configured = False
    try:
        logging_setup.configure_logging()
        assert redacao_log._installed
    finally:
        root.handlers[:] = originais
        root.setLevel(nivel)
        logging_setup._console, logging_setup._configured = estado


def test_flow_logger_carries_the_filter_even_outside_the_executor():
    from flow.utils.logger import get_logger

    logger = get_logger("flow.teste_filtro")
    fluxo = io.StringIO()
    handler = logging.StreamHandler(fluxo)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.handlers[:] = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.info("dsn=%s", DSN)
    assert "SenhaForte123" not in fluxo.getvalue()


def test_secret_in_use_is_replaced_before_the_patterns(isolated_factory):
    """The patterns stop at the first `%` of the value: running before the exact
    `segredos_vivos` replacement, they cut the needle and the key's tail leaked to the log."""
    from flow.utils import segredos_vivos

    redacao_log.install_in_process()
    chave = "Kq7vT9zR%2BaB3%2FxY5wL%3D%3D"  # pragma: allowlist secret
    logger, fluxo = _capture("urllib3.teste_ordem")
    with segredos_vivos.in_use(chave):
        # How urllib3 logs: the whole URL is ONE argument.
        logger.warning('"%s %s HTTP/1.1" %s', "GET", f"/ows?service=WFS&token={chave}", 200)
        # And the already-formatted message, with no arguments.
        logger.warning(f"falhou em /ows?service=WFS&token={chave}")
    saida = fluxo.getvalue()
    assert "aB3" not in saida and "xY5wL" not in saida
    assert saida.count("token=***") == 2


def test_simple_arguments_keep_their_shape_and_are_not_rescanned(isolated_factory, monkeypatch):
    redacao_log.install_in_process()
    chamadas = []
    original = redacao_log._scrub
    monkeypatch.setattr(redacao_log, "_scrub", lambda t: chamadas.append(t) or original(t))
    registro = logging.getLogger("x").makeRecord("x", logging.INFO, __file__, 1, "%s de %d", ("a", 3), None)
    assert registro.args == ("a", 3)
    assert "a de 3" not in chamadas  # the interpolated message was not rescanned


def test_traceback_formatted_once_stays_in_exc_text(isolated_factory):
    redacao_log.install_in_process()
    try:
        raise RuntimeError("sem segredo")
    except RuntimeError:
        import sys
        registro = logging.getLogger("x").makeRecord(
            "x", logging.ERROR, __file__, 1, "falhou", (), sys.exc_info(),
        )
    assert registro.exc_text and "RuntimeError: sem segredo" in registro.exc_text
    assert registro.exc_info is not None  # nothing redacted: the exception is still available
