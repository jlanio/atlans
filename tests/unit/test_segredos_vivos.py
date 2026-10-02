# tests/unit/test_segredos_vivos.py
"""Enquanto um segredo está em uso, nenhum registro de log do processo o leva —
venha de que biblioteca vier (o owslib e o urllib3 logam a URL de cada pedido,
com a chave authkey nela)."""
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
    # Abaixo de 6 caracteres a troca reescreveria datas, ids e contadores de
    # todo log do processo ("2024" em "2024-09-25").
    with caplog.at_level(logging.INFO):
        with segredos_vivos.em_uso("ab"), segredos_vivos.em_uso("2024"):
            logging.getLogger("x").info("job 2024-09-25 iniciado, tabela ab, request_id=ab2024cd")
    assert "job 2024-09-25 iniciado, tabela ab, request_id=ab2024cd" in _formatado(caplog)


def test_o_registro_mantem_a_forma_msg_e_args_redigidos_um_a_um(caplog):
    # Há formatadores que leem `record.args` (o de acesso do uvicorn desempacota
    # cinco campos dele): achatar `args` para None os quebrava e a linha se perdia.
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
    # `getMessage()` falha (um %s a mais); antes o registro seguia intacto e o
    # `handleError` do logging imprimia os argumentos crus no stderr. Um handler
    # próprio, e não o caplog: o do pytest relança o TypeError ao formatar.
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
    def _com_a_chave_na_pilha(segredo_na_pilha):  # o nome do argumento vai ao stack_info? não; o valor não
        logging.getLogger("x").info("com pilha", stack_info=True)

    with caplog.at_level(logging.INFO):
        with segredos_vivos.em_uso(CHAVE):
            _com_a_chave_na_pilha(CHAVE)
            # Uma pilha que carrega a chave (a linha de código com ela).
            registro = caplog.records[-1]
            registro.stack_info = f"Stack:\n  File x, line 1, in f\n    url = 'http://x/ows?authkey={CHAVE}'"
            segredos_vivos._limpar(registro, segredos_vivos._formas)
    assert CHAVE not in registro.stack_info and "authkey=***" in registro.stack_info


def test_a_fabrica_anterior_continua_sendo_chamada(caplog):
    # Quem instalou uma fábrica antes (um APM, um formatador de contexto) segue
    # vendo cada registro: a nossa envolve a dele, não a substitui.
    vistos = []
    anterior = logging.getLogRecordFactory()

    def _minha(*args, **kwargs):
        registro = anterior(*args, **kwargs)
        vistos.append(registro)
        return registro

    logging.setLogRecordFactory(_minha)
    try:
        segredos_vivos._instalada = False  # reinstala por cima da minha
        with caplog.at_level(logging.INFO):
            with segredos_vivos.em_uso(CHAVE):
                logging.getLogger("x").info("oi %s", CHAVE)
    finally:
        logging.setLogRecordFactory(anterior)
        segredos_vivos._instalada = False  # o próximo `em_uso` reinstala por cima da original
    assert vistos == caplog.records and _formatado(caplog) == "oi ***"


def test_a_forma_maior_e_trocada_inteira(caplog):
    with caplog.at_level(logging.INFO):
        with segredos_vivos.em_uso("abcdef", "abcdefgh"):
            logging.getLogger("x").info("k=abcdefgh")
    assert _formatado(caplog) == "k=***"


def test_o_formatador_de_console_do_executor_mostra_o_traceback_redigido(caplog):
    # A fábrica entrega o traceback redigido em `exc_text` e anula `exc_info`;
    # o console do executor só olhava `exc_info` e perdia o traceback inteiro.
    from executor.logging_setup import _ColoredFormatter
    with caplog.at_level(logging.ERROR):
        with segredos_vivos.em_uso(CHAVE):
            try:
                raise ConnectionError(f"Max retries exceeded with url: /ows?authkey={CHAVE}")
            except ConnectionError:
                logging.getLogger("flow.x").exception("falhou")
    saida = _ColoredFormatter("never").format(caplog.records[-1])
    assert "Traceback" in saida and "authkey=***" in saida and CHAVE not in saida
