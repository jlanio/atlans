# flow/utils/segredos_vivos.py
#
# The secrets in use right now, and no log record containing them.
#
# Third-party libraries log whatever they want: owslib and urllib3 write the URL
# of each request at DEBUG (the authkey key goes in the URL), and urllib3 repeats
# it in a WARNING when the server sends a malformed header — at the default
# level. A per-logger filter doesn't reach those records, and a per-handler
# filter would have to be on every handler the executor (and the panel)
# installs — the next handler would forget it. The LogRecord factory is the only
# point EVERY record in the process passes through: while a secret is in use
# (`em_uso`), every record containing it comes out with it replaced by `***` —
# the message, the arguments, the exception and the traceback.
#
# The record comes out with the SAME shape it went in: `msg` and each `args`
# redacted one by one, not `msg` already interpolated with `args = None`. Some
# formatters read `record.args` (uvicorn's access formatter unpacks five fields
# from it); flattening the arguments broke them, and the access line was lost.
#
# Outside an `em_uso` the cost is one empty-tuple test per record.
import logging
import threading
from collections import Counter
from contextlib import contextmanager

# The same minimum as `credencial_wfs.TAMANHO_MINIMO_DO_SEGREDO` (repeated so
# this module doesn't depend on that one): below it the replacement would mangle
# dates, ids and counters in every log of the process.
_TAMANHO_MINIMO = 6

_lock = threading.Lock()
_contagem: Counter = Counter()
# What the factory reads: a tuple swapped whole under the lock (the read, without
# a lock, never sees the Counter mid-change). Longest first, so that a form
# containing another is replaced whole.
_formas: tuple[str, ...] = ()
_instalada = False


def _redigir(texto: str, formas: tuple[str, ...]) -> str:
    for forma in formas:
        texto = texto.replace(forma, "***")
    return texto


def _tem(texto: str, formas: tuple[str, ...]) -> bool:
    return any(f in texto for f in formas)


def _redigir_valor(valor, formas: tuple[str, ...]):
    """A string redacted; anything else as it came (the `%r`/`%s` of an
    object whose repr carries the secret is caught by the interpolated message,
    in the next step)."""
    return _redigir(valor, formas) if isinstance(valor, str) else valor


def _limpar(registro: logging.LogRecord, formas: tuple[str, ...]) -> None:
    # 1. The record's shape preserved: `msg` and each argument, one by one.
    if isinstance(registro.msg, str):
        registro.msg = _redigir(registro.msg, formas)
    args = registro.args
    if isinstance(args, dict):
        registro.args = {k: _redigir_valor(v, formas) for k, v in args.items()}
    elif isinstance(args, tuple):
        registro.args = tuple(_redigir_valor(a, formas) for a in args)
    # 2. What only shows up interpolated (an object's repr, an argument that
    #    is not a string): here, yes, the finished message, without the arguments.
    #    A `%`-format that doesn't match the arguments fails here — and the record
    #    goes on with what step 1 already redacted, instead of intact.
    try:
        mensagem = registro.getMessage()
    except Exception:
        mensagem = None
    if mensagem is not None and _tem(mensagem, formas):
        registro.msg, registro.args = _redigir(mensagem, formas), None
    if registro.exc_info and not registro.exc_text:
        texto = logging.Formatter().formatException(registro.exc_info)
        if _tem(texto, formas):
            # The formatter uses the ready-made `exc_text` instead of formatting `exc_info`.
            registro.exc_text, registro.exc_info = _redigir(texto, formas), None
    if registro.stack_info and _tem(registro.stack_info, formas):
        registro.stack_info = _redigir(registro.stack_info, formas)


def _instalar() -> None:
    global _instalada
    anterior = logging.getLogRecordFactory()

    def fabrica(*args, **kwargs):
        registro = anterior(*args, **kwargs)
        formas = _formas
        if formas:
            try:
                _limpar(registro, formas)
            except Exception:  # logging never brings down the caller
                pass
        return registro

    logging.setLogRecordFactory(fabrica)
    _instalada = True


def _publicar() -> None:
    global _formas
    _formas = tuple(sorted((f for f, n in _contagem.items() if n > 0), key=len, reverse=True))


@contextmanager
def em_uso(*formas: str):
    """While the block runs, no log record in the process carries `formas`.

    Counted per form: two nodes with the same key in parallel — the first to
    finish does not release it while the other is still using it.
    """
    formas = tuple({f for f in formas if f and len(f) >= _TAMANHO_MINIMO})
    with _lock:
        if not _instalada:
            _instalar()
        _contagem.update(formas)
        _publicar()
    try:
        yield
    finally:
        with _lock:
            _contagem.subtract(formas)
            for f in formas:
                if _contagem[f] <= 0:
                    del _contagem[f]
            _publicar()
