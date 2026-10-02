# flow/utils/segredos_vivos.py
#
# Os segredos em uso agora, e nenhum registro de log com eles.
#
# Biblioteca de terceiro loga o que quer: o owslib e o urllib3 escrevem em
# DEBUG a URL de cada pedido (a chave authkey vai na URL), e o urllib3 a repete
# num WARNING quando o servidor manda um cabeçalho malformado — no nível
# padrão. Um filtro por logger não alcança esses registros, e um filtro por
# handler teria de estar em cada handler que o executor (e o painel) instala —
# o próximo handler o esqueceria. A fábrica de LogRecord é o único ponto por
# onde TODO registro do processo passa: enquanto um segredo está em uso
# (`em_uso`), cada registro que o contém sai com ele trocado por `***` — a
# mensagem, os argumentos, a exceção e a pilha.
#
# O registro sai com a MESMA forma que entrou: `msg` e cada `args` redigidos
# um a um, e não `msg` já interpolada com `args = None`. Há formatadores que
# leem `record.args` (o de acesso do uvicorn desempacota cinco campos dele);
# achatar os argumentos os quebrava, e a linha de acesso se perdia.
#
# Fora de um `em_uso` o custo é um teste de tupla vazia por registro.
import logging
import threading
from collections import Counter
from contextlib import contextmanager

# O mesmo mínimo de `credencial_wfs.TAMANHO_MINIMO_DO_SEGREDO` (repetido para
# este módulo não depender daquele): abaixo disto a troca mutilaria datas, ids
# e contadores de todo log do processo.
_TAMANHO_MINIMO = 6

_lock = threading.Lock()
_contagem: Counter = Counter()
# O que a fábrica lê: uma tupla trocada inteira sob o lock (a leitura, sem
# lock, nunca vê o Counter no meio de uma mudança). Maiores primeiro, para
# uma forma que contém outra ser trocada inteira.
_formas: tuple[str, ...] = ()
_instalada = False


def _redigir(texto: str, formas: tuple[str, ...]) -> str:
    for forma in formas:
        texto = texto.replace(forma, "***")
    return texto


def _tem(texto: str, formas: tuple[str, ...]) -> bool:
    return any(f in texto for f in formas)


def _redigir_valor(valor, formas: tuple[str, ...]):
    """Uma string redigida; qualquer outra coisa como veio (o `%r`/`%s` de um
    objeto cuja repr carregue o segredo é apanhado pela mensagem interpolada,
    no passo seguinte)."""
    return _redigir(valor, formas) if isinstance(valor, str) else valor


def _limpar(registro: logging.LogRecord, formas: tuple[str, ...]) -> None:
    # 1. A forma do registro preservada: `msg` e cada argumento, um a um.
    if isinstance(registro.msg, str):
        registro.msg = _redigir(registro.msg, formas)
    args = registro.args
    if isinstance(args, dict):
        registro.args = {k: _redigir_valor(v, formas) for k, v in args.items()}
    elif isinstance(args, tuple):
        registro.args = tuple(_redigir_valor(a, formas) for a in args)
    # 2. O que só aparece interpolado (a repr de um objeto, um argumento que
    #    não é string): aí sim a mensagem pronta, sem os argumentos. Um
    #    `%`-format que não bate com os argumentos falha aqui — e o registro
    #    segue com o que o passo 1 já redigiu, em vez de intacto.
    try:
        mensagem = registro.getMessage()
    except Exception:
        mensagem = None
    if mensagem is not None and _tem(mensagem, formas):
        registro.msg, registro.args = _redigir(mensagem, formas), None
    if registro.exc_info and not registro.exc_text:
        texto = logging.Formatter().formatException(registro.exc_info)
        if _tem(texto, formas):
            # O formatter usa `exc_text` pronto em vez de formatar `exc_info`.
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
            except Exception:  # o log nunca derruba quem loga
                pass
        return registro

    logging.setLogRecordFactory(fabrica)
    _instalada = True


def _publicar() -> None:
    global _formas
    _formas = tuple(sorted((f for f, n in _contagem.items() if n > 0), key=len, reverse=True))


@contextmanager
def em_uso(*formas: str):
    """Enquanto o bloco roda, nenhum registro de log do processo leva `formas`.

    Contado por forma: dois nós com a mesma chave em paralelo — o primeiro a
    terminar não a libera enquanto o outro ainda a usa.
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
