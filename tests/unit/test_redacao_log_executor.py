"""A redação de segredos por padrão vale também no executor e no flow.

A lista (DSN com senha, Bearer, Basic, PAT...) vivia em `app/core/utils/logger`
e só os loggers do app a usavam: o executor, que decifra DSN e monta cabeçalho
de autenticação, logava tudo sem máscara. Agora ela mora no flow/, o app a
reexporta, e o executor a liga na fábrica de LogRecord.
"""
import io
import logging

import pytest

from flow.utils import redacao_log

DSN = "postgresql://leitor:SenhaForte123@db.interno:5432/geo"  # pragma: allowlist secret
BEARER = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.assinaturaassinatura"  # pragma: allowlist secret


@pytest.fixture
def fabrica_isolada():
    fabrica, instalada = logging.getLogRecordFactory(), redacao_log._instalada
    redacao_log._instalada = False
    yield
    logging.setLogRecordFactory(fabrica)
    redacao_log._instalada = instalada


def _capturar(nome: str):
    fluxo = io.StringIO()
    handler = logging.StreamHandler(fluxo)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger(nome)
    logger.handlers[:] = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger, fluxo


def test_app_reexporta_a_mesma_lista():
    from app.core.utils import logger as app_logger

    assert app_logger.scrub_text is redacao_log.scrub_text
    assert app_logger._SCRUB_PATTERNS is redacao_log._SCRUB_PATTERNS


def test_fabrica_redige_logger_de_terceiro_sem_filtro(fabrica_isolada):
    """O handler/logger de terceiro não tem filtro nenhum: é a fábrica que pega."""
    redacao_log.instalar_no_processo()
    logger, fluxo = _capturar("asyncpg.terceiro")
    logger.error("falhou em %s com %s", DSN, BEARER)
    saida = fluxo.getvalue()
    assert "SenhaForte123" not in saida and "assinaturaassinatura" not in saida
    assert "db.interno" in saida  # o diagnóstico continua útil


def test_argumento_que_nao_e_string_tambem_e_redigido(fabrica_isolada):
    """A exceção do driver traz a DSN no `str()` — `%s` de um objeto."""
    redacao_log.instalar_no_processo()
    logger, fluxo = _capturar("executor.teste_objeto")
    logger.error("conexão recusada: %s", ConnectionError(f"não conectou em {DSN}"))
    assert "SenhaForte123" not in fluxo.getvalue()


def test_traceback_e_redigido(fabrica_isolada):
    redacao_log.instalar_no_processo()
    logger, fluxo = _capturar("executor.teste_traceback")
    try:
        raise RuntimeError(f"erro com {DSN}")
    except RuntimeError:
        logger.exception("falha no nó")
    assert "SenhaForte123" not in fluxo.getvalue()
    assert "RuntimeError" in fluxo.getvalue()


def test_registro_sem_segredo_mantem_a_forma(fabrica_isolada):
    """Há formatadores que leem `record.args` (o de acesso do uvicorn)."""
    redacao_log.instalar_no_processo()
    registro = logging.getLogger("x").makeRecord("x", logging.INFO, __file__, 1, "%s %s", ("a", "b"), None)
    assert registro.args == ("a", "b")


def test_instalar_e_idempotente(fabrica_isolada):
    redacao_log.instalar_no_processo()
    primeira = logging.getLogRecordFactory()
    redacao_log.instalar_no_processo()
    assert logging.getLogRecordFactory() is primeira


def test_configure_logging_do_executor_liga_a_redacao(fabrica_isolada, monkeypatch):
    from executor import logging_setup

    root = logging.getLogger()
    originais, nivel = list(root.handlers), root.level
    estado = (logging_setup._console, logging_setup._configurado)
    logging_setup._configurado = False
    try:
        logging_setup.configure_logging()
        assert redacao_log._instalada
    finally:
        root.handlers[:] = originais
        root.setLevel(nivel)
        logging_setup._console, logging_setup._configurado = estado


def test_logger_do_flow_leva_o_filtro_mesmo_fora_do_executor():
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


def test_segredo_em_uso_e_trocado_antes_dos_padroes(fabrica_isolada):
    """Os padrões param no primeiro `%` do valor: rodando antes da troca exata
    de `segredos_vivos`, cortavam a agulha e a cauda da chave saía no log."""
    from flow.utils import segredos_vivos

    redacao_log.instalar_no_processo()
    chave = "Kq7vT9zR%2BaB3%2FxY5wL%3D%3D"  # pragma: allowlist secret
    logger, fluxo = _capturar("urllib3.teste_ordem")
    with segredos_vivos.em_uso(chave):
        # Como o urllib3 loga: a URL inteira é UM argumento.
        logger.warning('"%s %s HTTP/1.1" %s', "GET", f"/ows?service=WFS&token={chave}", 200)
        # E a mensagem já pronta, sem argumentos.
        logger.warning(f"falhou em /ows?service=WFS&token={chave}")
    saida = fluxo.getvalue()
    assert "aB3" not in saida and "xY5wL" not in saida
    assert saida.count("token=***") == 2


def test_argumentos_simples_mantem_a_forma_e_nao_reescaneiam(fabrica_isolada, monkeypatch):
    redacao_log.instalar_no_processo()
    chamadas = []
    original = redacao_log._scrub
    monkeypatch.setattr(redacao_log, "_scrub", lambda t: chamadas.append(t) or original(t))
    registro = logging.getLogger("x").makeRecord("x", logging.INFO, __file__, 1, "%s de %d", ("a", 3), None)
    assert registro.args == ("a", 3)
    assert "a de 3" not in chamadas  # a mensagem interpolada não foi reescaneada


def test_traceback_formatado_uma_vez_fica_em_exc_text(fabrica_isolada):
    redacao_log.instalar_no_processo()
    try:
        raise RuntimeError("sem segredo")
    except RuntimeError:
        import sys
        registro = logging.getLogger("x").makeRecord(
            "x", logging.ERROR, __file__, 1, "falhou", (), sys.exc_info(),
        )
    assert registro.exc_text and "RuntimeError: sem segredo" in registro.exc_text
    assert registro.exc_info is not None  # nada redigido: a exceção continua disponível
