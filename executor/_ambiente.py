# executor/_ambiente.py
"""
Leitura de numeros do ambiente do executor — o ponto unico.

Valor invalido no `.env` (nao numerico, ou fora da faixa) e erro de digitacao,
nao intencao: vira o padrao, com um aviso dizendo qual variavel e qual valor, e
NUNCA derruba o import. Havia duas copias deste leitor (executor/config.py e
executor/sync/sync_config.py, com contratos diferentes) e cinco
`int(os.getenv(...))` crus em job_validator.py e renewal.py — com eles, um
`EXECUTOR_CLOCK_SKEW_SECONDS=abc` matava o processo com ValueError no import,
antes de main() rodar e antes de o canal com o supervisor subir.

O aviso e ADIADO enquanto o logging nao esta configurado: executor/config.py e
importado antes de configure_logging(), e um aviso emitido ali cairia no
logging.lastResort (stderr cru, sem formato — com o painel ligado, lixo por
cima do desenho). Ele fica retido ate configure_logging() chamar
emitir_avisos_adiados() (via executor.config.flush_startup_warnings). Dali em
diante os avisos saem DIRETO: job_validator, renewal e sync_config sao
importados depois do boot, e nao haveria outro flush para entrega-los.
"""
from __future__ import annotations

import logging
import math
import os

logger = logging.getLogger(__name__)

_AVISOS_ADIADOS: list[tuple[str, tuple]] = []
_logging_pronto = False


def avisar(msg: str, *args) -> None:
    """Aviso de configuracao: retido ate o logging subir, direto depois."""
    if _logging_pronto:
        logger.warning(msg, *args)
    else:
        _AVISOS_ADIADOS.append((msg, args))


def emitir_avisos_adiados() -> None:
    """Emite os avisos retidos, agora que ha handlers de verdade."""
    global _logging_pronto
    for msg, args in _AVISOS_ADIADOS:
        logger.warning(msg, *args)
    _AVISOS_ADIADOS.clear()
    _logging_pronto = True


def _faixa(minimo, maximo) -> str:
    return f">= {minimo}" if maximo is None else f"entre {minimo} e {maximo}"


def ler_int(nome: str, padrao: int, minimo: int = 1, maximo: int | None = None) -> int:
    """Inteiro do ambiente dentro de [minimo, maximo]; fora disso, o padrao com aviso.

    Ausente ou em branco e o padrao, sem aviso. A faixa existe porque o valor
    absurdo nao falha — ele funciona errado: `EXECUTOR_MAX_CONCURRENT=0` subia o
    executor SEM worker nenhum, online, reportando capacity 0 (e por isso o
    PREFERIDO pelo scheduler least-loaded do servidor), dando ACK nos jobs e
    nunca executando — runs presos em 'running' para sempre.
    """
    bruto = os.getenv(nome)
    if bruto is None or not bruto.strip():
        return padrao
    try:
        valor = int(bruto.strip())
    except ValueError:
        avisar("%s=%r nao e um inteiro — usando o padrao %d.", nome, bruto, padrao)
        return padrao
    if valor < minimo or (maximo is not None and valor > maximo):
        avisar("%s=%d fora da faixa (%s) — usando o padrao %d.",
               nome, valor, _faixa(minimo, maximo), padrao)
        return padrao
    return valor


def ler_float(nome: str, padrao: float, minimo: float, maximo: float | None = None) -> float:
    """Versao float de ler_int. `nan` e `inf` nao sao numero para este fim."""
    bruto = os.getenv(nome)
    if bruto is None or not bruto.strip():
        return padrao
    try:
        valor = float(bruto.strip())
    except ValueError:
        valor = math.nan
    if not math.isfinite(valor):
        avisar("%s=%r nao e um numero — usando o padrao %s.", nome, bruto, padrao)
        return padrao
    if valor < minimo or (maximo is not None and valor > maximo):
        avisar("%s=%s fora da faixa (%s) — usando o padrao %s.",
               nome, valor, _faixa(minimo, maximo), padrao)
        return padrao
    return valor
