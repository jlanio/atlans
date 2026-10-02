# executor/dashboard/log_sink.py
"""
Handler que alimenta o rodape de alertas do painel.
"""
from __future__ import annotations

import logging

from executor.logging_setup import LEVEL_LABEL, alias_for


class LogTailHandler(logging.Handler):
    """Encaminha WARNING+ para o coletor, que os guarda num ring buffer.

    E o unico ponto em que o painel toca o pipeline de logging — e de proposito:
    aqui o texto da mensagem *e* o dado. Nenhuma estatistica sai daqui; elas vem
    dos hooks estruturados.

    Sem este bloco o painel seria ativamente pior que o log: um executor em loop
    de reconexao mostraria contadores subindo e nenhuma pista da causa.

    Formata no `emit`, e nao no render: guardar `LogRecord` vivo seguraria
    tambem tudo que `record.args` referencia, por minutos.
    """

    def __init__(self, stats, level: int = logging.WARNING):
        super().__init__(level=level)
        self._stats = stats

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._stats.on_log_record(
                record,
                alias_for(record.name),
                LEVEL_LABEL.get(record.levelno, record.levelname[:5]),
            )
        except Exception:
            pass  # handleError() escreveria no stderr — exatamente o que o painel ocupa


class JsonLogHandler(LogTailHandler):
    """Alem de alimentar o ring buffer, emite `{"t":"log"}` no canal NDJSON.

    Herda de `LogTailHandler` de proposito: o painel de alertas da GUI e o
    rodape do painel rich mostram a MESMA informacao, e ter duas extracoes do
    `LogRecord` seria a porta de entrada para elas divergirem.

    O `emit` do pai nunca levanta, entao o evento sai mesmo que o coletor
    engasgue com o registro.
    """

    def __init__(self, stats, runtime, level: int = logging.WARNING):
        super().__init__(stats, level=level)
        self._runtime = runtime

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        try:
            self._runtime.emitir("log", {
                "ts": record.created,
                "level": LEVEL_LABEL.get(record.levelno, record.levelname[:5]).strip(),
                "alias": alias_for(record.name).strip(),
                "logger": record.name,
                "msg": record.getMessage(),
            })
        except Exception:
            # Nao logar aqui: um logger.error() dentro de um handler de log e
            # recursao — o proximo emit chamaria este mesmo bloco.
            pass
