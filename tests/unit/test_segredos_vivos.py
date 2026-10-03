# tests/unit/test_segredos_vivos.py
"""While a secret is in use, no log record of the process carries it — whatever
library it comes from (owslib and urllib3 log the URL of every request, with
the authkey in it)."""
import logging

from flow.utils import segredos_vivos

CHAVE = "c0ffee-SEGREDO-42"


def _formatado(caplog) -> str:
    formato = logging.Formatter("%(message)s")
    return "\n".join(formato.format(r) for r in caplog.records)


def test_o_warning_do_urllib3_e_o_debug_do_owslib_saem_sem_a_chave(caplog):
    with caplog.at_level(logging.DEBUG):
        with segredos_vivos.em_uso(CHAVE):
            logging.getLogger("urllib3.connection").warning(
                "Failed to parse headers (url=%s): %s", f"http://x/ows?authkey={CHAVE}", "cabeçalho torto",
            )
            logging.getLogger("owslib").debug("building WFS http://x/ows?authkey=%s", CHAVE)
    texto = _formatado(caplog)
    assert CHAVE not in texto and texto.count("authkey=***") == 2


def test_a_excecao_logada_tambem_sai_sem_a_chave(caplog):
    with caplog.at_level(logging.ERROR):
        with segredos_vivos.em_uso(CHAVE):
            try:
                raise ConnectionError(f"Max retries exceeded with url: /ows?authkey={CHAVE}")
            except ConnectionError:
                logging.getLogger("qualquer.biblioteca").exception("falhou")
    texto = _formatado(caplog)
    assert "ConnectionError: Max retries exceeded" in texto and CHAVE not in texto


def test_fora_do_bloco_o_log_segue_intacto(caplog):
    with segredos_vivos.em_uso(CHAVE):
        pass
    with caplog.at_level(logging.INFO):
        logging.getLogger("x").info("valor %s", CHAVE)
    assert CHAVE in _formatado(caplog)


def test_contado_por_uso_um_no_que_termina_nao_libera_o_do_outro(caplog):
    with caplog.at_level(logging.INFO):
        with segredos_vivos.em_uso(CHAVE):
            with segredos_vivos.em_uso(CHAVE):
                pass
            logging.getLogger("x").info("ainda em uso: %s", CHAVE)
    assert CHAVE not in _formatado(caplog)


def test_segredo_curto_demais_nao_mutila_o_log(caplog):
    # Below 6 characters the replacement would rewrite dates, ids and counters in
    # every log of the process ("2024" in "2024-09-25").
    with caplog.at_level(logging.INFO):
        with segredos_vivos.em_uso("ab"), segredos_vivos.em_uso("2024"):
            logging.getLogger("x").info("job 2024-09-25 iniciado, tabela ab, request_id=ab2024cd")
    assert "job 2024-09-25 iniciado, tabela ab, request_id=ab2024cd" in _formatado(caplog)


def test_o_registro_mantem_a_forma_msg_e_args_redigidos_um_a_um(caplog):
    # Some formatters read `record.args` (uvicorn's access one unpacks five fields
    # from it): flattening `args` to None broke them and the line was lost.
    class _ComoOUvicorn(logging.Formatter):
        def format(self, record):
            cliente, metodo, caminho, versao, status = record.args
            return f'{cliente} - "{metodo} {caminho} HTTP/{versao}" {status}'

    with caplog.at_level(logging.INFO):
        with segredos_vivos.em_uso(CHAVE):
            logging.getLogger("uvicorn.access").info(
                '%s - "%s %s HTTP/%s" %d', "10.0.0.7:5555", "GET", f"/api/x?authkey={CHAVE}", "1.1", 200,
            )
    (registro,) = caplog.records
    assert registro.args[2] == "/api/x?authkey=***" and registro.args[4] == 200
    assert _ComoOUvicorn().format(registro) == '10.0.0.7:5555 - "GET /api/x?authkey=*** HTTP/1.1" 200'


def test_formato_que_nao_bate_com_os_argumentos_nao_deixa_o_segredo_passar():
    # `getMessage()` fails (one %s too many); before, the record went through intact
    # and logging's `handleError` printed the raw arguments to stderr. A handler of
    # our own, not caplog: pytest's re-raises the TypeError when formatting.
    class _Guarda(logging.Handler):
        def __init__(self):
            super().__init__()
            self.registros = []

        def emit(self, record):
            self.registros.append(record)

    logger, guarda = logging.getLogger("teste.formato.torto"), _Guarda()
    logger.propagate, logger.level = False, logging.INFO
    logger.addHandler(guarda)
    try:
        with segredos_vivos.em_uso(CHAVE):
            logger.info("url=%s extra=%s", f"http://x/ows?authkey={CHAVE}")
    finally:
        logger.removeHandler(guarda)
        logger.propagate = True
    (registro,) = guarda.registros
    assert registro.args == ("http://x/ows?authkey=***",)
    assert CHAVE not in repr(registro.__dict__)


def test_a_repr_de_um_objeto_nos_argumentos_e_apanhada_pela_mensagem_pronta(caplog):
    class _Pedido:
        def __repr__(self):
            return f"<Pedido url=http://x/ows?authkey={CHAVE}>"

    with caplog.at_level(logging.INFO):
        with segredos_vivos.em_uso(CHAVE):
            logging.getLogger("x").info("enviando %r", _Pedido())
    assert CHAVE not in _formatado(caplog) and "authkey=***" in _formatado(caplog)


def test_stack_info_tambem_sai_sem_a_chave(caplog):
    def _com_a_chave_na_pilha(segredo_na_pilha):  # does the argument name go to stack_info? no; the value does not
        logging.getLogger("x").info("com pilha", stack_info=True)

    with caplog.at_level(logging.INFO):
        with segredos_vivos.em_uso(CHAVE):
            _com_a_chave_na_pilha(CHAVE)
            # A stack that carries the key (the line of code containing it).
            registro = caplog.records[-1]
            registro.stack_info = f"Stack:\n  File x, line 1, in f\n    url = 'http://x/ows?authkey={CHAVE}'"
            segredos_vivos._limpar(registro, segredos_vivos._formas)
    assert CHAVE not in registro.stack_info and "authkey=***" in registro.stack_info


def test_a_fabrica_anterior_continua_sendo_chamada(caplog):
    # Whoever installed a factory before (an APM, a context formatter) still sees
    # every record: ours wraps theirs, it does not replace it.
    vistos = []
    anterior = logging.getLogRecordFactory()

    def _minha(*args, **kwargs):
        registro = anterior(*args, **kwargs)
        vistos.append(registro)
        return registro

    logging.setLogRecordFactory(_minha)
    try:
        segredos_vivos._instalada = False  # reinstalls on top of mine
        with caplog.at_level(logging.INFO):
            with segredos_vivos.em_uso(CHAVE):
                logging.getLogger("x").info("oi %s", CHAVE)
    finally:
        logging.setLogRecordFactory(anterior)
        segredos_vivos._instalada = False  # the next `em_uso` reinstalls on top of the original
    assert vistos == caplog.records and _formatado(caplog) == "oi ***"


def test_a_forma_maior_e_trocada_inteira(caplog):
    with caplog.at_level(logging.INFO):
        with segredos_vivos.em_uso("abcdef", "abcdefgh"):
            logging.getLogger("x").info("k=abcdefgh")
    assert _formatado(caplog) == "k=***"


def test_o_formatador_de_console_do_executor_mostra_o_traceback_redigido(caplog):
    # The factory delivers the redacted traceback in `exc_text` and nulls `exc_info`;
    # the executor console only looked at `exc_info` and lost the whole traceback.
    from executor.logging_setup import _ColoredFormatter
    with caplog.at_level(logging.ERROR):
        with segredos_vivos.em_uso(CHAVE):
            try:
                raise ConnectionError(f"Max retries exceeded with url: /ows?authkey={CHAVE}")
            except ConnectionError:
                logging.getLogger("flow.x").exception("falhou")
    saida = _ColoredFormatter("never").format(caplog.records[-1])
    assert "Traceback" in saida and "authkey=***" in saida and CHAVE not in saida
