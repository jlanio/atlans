# tests/unit/test_segredos_vivos.py
"""While a secret is in use, no log record of the process carries it — whatever
library it comes from (owslib and urllib3 log the URL of every request, with
the authkey in it)."""
import logging

from flow.utils import segredos_vivos

CHAVE = "c0ffee-SEGREDO-42"


def _formatted(caplog) -> str:
    formato = logging.Formatter("%(message)s")
    return "\n".join(formato.format(r) for r in caplog.records)


def test_the_urllib3_warning_and_owslib_debug_come_out_without_the_key(caplog):
    with caplog.at_level(logging.DEBUG):
        with segredos_vivos.in_use(CHAVE):
            logging.getLogger("urllib3.connection").warning(
                "Failed to parse headers (url=%s): %s", f"http://x/ows?authkey={CHAVE}", "cabeçalho torto",
            )
            logging.getLogger("owslib").debug("building WFS http://x/ows?authkey=%s", CHAVE)
    texto = _formatted(caplog)
    assert CHAVE not in texto and texto.count("authkey=***") == 2


def test_the_logged_exception_also_comes_out_without_the_key(caplog):
    with caplog.at_level(logging.ERROR):
        with segredos_vivos.in_use(CHAVE):
            try:
                raise ConnectionError(f"Max retries exceeded with url: /ows?authkey={CHAVE}")
            except ConnectionError:
                logging.getLogger("qualquer.biblioteca").exception("falhou")
    texto = _formatted(caplog)
    assert "ConnectionError: Max retries exceeded" in texto and CHAVE not in texto


def test_outside_the_block_the_log_stays_intact(caplog):
    with segredos_vivos.in_use(CHAVE):
        pass
    with caplog.at_level(logging.INFO):
        logging.getLogger("x").info("valor %s", CHAVE)
    assert CHAVE in _formatted(caplog)


def test_counted_per_use_a_finishing_node_does_not_release_the_others(caplog):
    with caplog.at_level(logging.INFO):
        with segredos_vivos.in_use(CHAVE):
            with segredos_vivos.in_use(CHAVE):
                pass
            logging.getLogger("x").info("ainda em uso: %s", CHAVE)
    assert CHAVE not in _formatted(caplog)


def test_too_short_secret_does_not_mangle_the_log(caplog):
    # Below 6 characters the replacement would rewrite dates, ids and counters in
    # every log of the process ("2024" in "2024-09-25").
    with caplog.at_level(logging.INFO):
        with segredos_vivos.in_use("ab"), segredos_vivos.in_use("2024"):
            logging.getLogger("x").info("job 2024-09-25 iniciado, tabela ab, request_id=ab2024cd")
    assert "job 2024-09-25 iniciado, tabela ab, request_id=ab2024cd" in _formatted(caplog)


def test_the_record_keeps_its_shape_msg_and_args_redacted_one_by_one(caplog):
    # Some formatters read `record.args` (uvicorn's access one unpacks five fields
    # from it): flattening `args` to None broke them and the line was lost.
    class _LikeUvicorn(logging.Formatter):
        def format(self, record):
            cliente, metodo, caminho, versao, status = record.args
            return f'{cliente} - "{metodo} {caminho} HTTP/{versao}" {status}'

    with caplog.at_level(logging.INFO):
        with segredos_vivos.in_use(CHAVE):
            logging.getLogger("uvicorn.access").info(
                '%s - "%s %s HTTP/%s" %d', "10.0.0.7:5555", "GET", f"/api/x?authkey={CHAVE}", "1.1", 200,
            )
    (registro,) = caplog.records
    assert registro.args[2] == "/api/x?authkey=***" and registro.args[4] == 200
    assert _LikeUvicorn().format(registro) == '10.0.0.7:5555 - "GET /api/x?authkey=*** HTTP/1.1" 200'


def test_format_mismatching_the_arguments_does_not_let_the_secret_through():
    # `getMessage()` fails (one %s too many); before, the record went through intact
    # and logging's `handleError` printed the raw arguments to stderr. A handler of
    # our own, not caplog: pytest's re-raises the TypeError when formatting.
    class _Guard(logging.Handler):
        def __init__(self):
            super().__init__()
            self.registros = []

        def emit(self, record):
            self.registros.append(record)

    logger, guarda = logging.getLogger("teste.formato.torto"), _Guard()
    logger.propagate, logger.level = False, logging.INFO
    logger.addHandler(guarda)
    try:
        with segredos_vivos.in_use(CHAVE):
            logger.info("url=%s extra=%s", f"http://x/ows?authkey={CHAVE}")
    finally:
        logger.removeHandler(guarda)
        logger.propagate = True
    (registro,) = guarda.registros
    assert registro.args == ("http://x/ows?authkey=***",)
    assert CHAVE not in repr(registro.__dict__)


def test_an_object_repr_in_the_arguments_is_caught_by_the_final_message(caplog):
    class _Request:
        def __repr__(self):
            return f"<Pedido url=http://x/ows?authkey={CHAVE}>"

    with caplog.at_level(logging.INFO):
        with segredos_vivos.in_use(CHAVE):
            logging.getLogger("x").info("enviando %r", _Request())
    assert CHAVE not in _formatted(caplog) and "authkey=***" in _formatted(caplog)


def test_stack_info_also_comes_out_without_the_key(caplog):
    def _with_the_key_on_the_stack(secret_on_stack):  # does the argument name go to stack_info? no; the value does not
        logging.getLogger("x").info("com pilha", stack_info=True)

    with caplog.at_level(logging.INFO):
        with segredos_vivos.in_use(CHAVE):
            _with_the_key_on_the_stack(CHAVE)
            # A stack that carries the key (the line of code containing it).
            registro = caplog.records[-1]
            registro.stack_info = f"Stack:\n  File x, line 1, in f\n    url = 'http://x/ows?authkey={CHAVE}'"
            segredos_vivos._clean(registro, segredos_vivos._forms)
    assert CHAVE not in registro.stack_info and "authkey=***" in registro.stack_info


def test_the_previous_factory_is_still_called(caplog):
    # Whoever installed a factory before (an APM, a context formatter) still sees
    # every record: ours wraps theirs, it does not replace it.
    vistos = []
    anterior = logging.getLogRecordFactory()

    def _ours(*args, **kwargs):
        registro = anterior(*args, **kwargs)
        vistos.append(registro)
        return registro

    logging.setLogRecordFactory(_ours)
    try:
        segredos_vivos._installed = False  # reinstalls on top of mine
        with caplog.at_level(logging.INFO):
            with segredos_vivos.in_use(CHAVE):
                logging.getLogger("x").info("oi %s", CHAVE)
    finally:
        logging.setLogRecordFactory(anterior)
        segredos_vivos._installed = False  # the next `in_use` reinstalls on top of the original
    assert vistos == caplog.records and _formatted(caplog) == "oi ***"


def test_the_longer_form_is_replaced_whole(caplog):
    with caplog.at_level(logging.INFO):
        with segredos_vivos.in_use("abcdef", "abcdefgh"):
            logging.getLogger("x").info("k=abcdefgh")
    assert _formatted(caplog) == "k=***"


def test_the_executor_console_formatter_shows_the_redacted_traceback(caplog):
    # The factory delivers the redacted traceback in `exc_text` and nulls `exc_info`;
    # the executor console only looked at `exc_info` and lost the whole traceback.
    from executor.logging_setup import _ColoredFormatter
    with caplog.at_level(logging.ERROR):
        with segredos_vivos.in_use(CHAVE):
            try:
                raise ConnectionError(f"Max retries exceeded with url: /ows?authkey={CHAVE}")
            except ConnectionError:
                logging.getLogger("flow.x").exception("falhou")
    saida = _ColoredFormatter("never").format(caplog.records[-1])
    assert "Traceback" in saida and "authkey=***" in saida and CHAVE not in saida
