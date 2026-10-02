# executor/logging_setup.py
"""
Configuracao de logging do executor.

Extraido de main.py, que carregava 130 linhas de setup de logging antes da
primeira linha de logica. Aqui mora tudo: formatter colorido do console,
handlers rotativos de arquivo e a comutacao para o modo painel.

Dois modos:

  CONSOLE (padrao)  — identico ao comportamento historico: um StreamHandler
                      colorido SEM filtro no root, mais os arquivos opcionais
                      de LOG_FILE_AGENT / LOG_FILE_WORKFLOW (filtrados).

  PAINEL            — o console sai do root e um handler rotativo CATCH-ALL
                      entra no lugar. O terminal fica livre para o dashboard
                      e nada se perde: o arquivo passa a ser o espelho fiel
                      do que ia para a tela.

A distincao entre "filtrado" e "catch-all" importa e nao e detalhe: o console
nunca teve filtro, entao ele levava ao terminal `websockets`, `asyncio`,
`boto3` e qualquer biblioteca de terceiro. Os handlers de arquivo existentes
sao filtrados por prefixo (`executor`/`httpx` e `flow`/`node`/`app`) e juntos
NAO cobrem esses loggers. Trocar o console por eles perderia registros — o
oposto do objetivo, que e mover o log passo-a-passo para disco, nao apaga-lo.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import pathlib
import sys

_LOG_FORMAT = "%(asctime)s  %(levelname)-5s  %(name)s  %(message)s"  # usado nos arquivos

_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5

# As variaveis sao lidas do ambiente, e nao de `executor.config`, para este
# modulo nao ter dependencia nenhuma dentro do pacote — mas a leitura acontece
# em `configure_logging()`, NUNCA no import. Quem popula o ambiente com o
# conteudo do `.env` e o `load_dotenv()` de config.py; ler no import tornaria o
# resultado dependente da ordem em que os modulos sao importados, e um
# `LOG_LEVEL=DEBUG` no .env seria silenciosamente ignorado.
_log_color = "auto"


def _nivel() -> int:
    return getattr(logging, os.getenv("LOG_LEVEL", "INFO").strip().upper(), logging.INFO)


class LoggingSetupError(RuntimeError):
    """Falha ao preparar o log em arquivo — o painel NAO deve ligar."""


def _rotating(path: str) -> logging.handlers.RotatingFileHandler:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    return logging.handlers.RotatingFileHandler(
        path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )


class _PrefixFilter(logging.Filter):
    """Aceita apenas registros cujo logger começa com um dos prefixos fornecidos."""
    def __init__(self, *prefixes: str):
        super().__init__()
        self._prefixes = prefixes

    def filter(self, record: logging.LogRecord) -> bool:
        return any(record.name == p or record.name.startswith(p + ".") for p in self._prefixes)


# ── Formatter colorido para console ──────────────────────────────────────────

_R   = "\033[0m"   # reset
_B   = "\033[1m"   # bold
_DIM = "\033[2m"   # dim

_LEVEL_COLOR = {
    logging.DEBUG:    "\033[37m",   # branco/cinza
    logging.INFO:     "\033[36m",   # ciano
    logging.WARNING:  "\033[33m",   # amarelo
    logging.ERROR:    "\033[31m",   # vermelho
    logging.CRITICAL: "\033[35m",   # magenta
}
LEVEL_LABEL = {
    logging.DEBUG:    "DEBUG",
    logging.INFO:     "INFO ",
    logging.WARNING:  "WARN ",
    logging.ERROR:    "ERROR",
    logging.CRITICAL: "CRIT ",
}
# Aliases de 6 chars por subsistema. Publico porque o rodape do painel os
# reusa como coluna de origem — a mesma taxonomia nos dois lugares.
LOGGER_ALIAS: dict[str, str] = {
    "executor":                 "AGENT ",
    "executor.connection":      "CONN  ",
    "executor.job_queue":       "QUEUE ",
    "executor.job_executor":    "EXEC  ",
    "executor.event_publisher": "EVENT ",
    "executor.job_validator":   "VALID ",
    "executor.crypto":          "CRYPTO",
    "executor.sync":            "SYNC  ",
    "executor.sync.manager":    "SYNC  ",
    "executor.sync.uploader":   "SYNC  ",
    "executor.sync.downloader": "SYNC  ",
    "executor.sync.watcher":    "SYNC  ",
    "httpx":                 "HTTP  ",
    "flow":                  "FLOW  ",
}


def alias_for(name: str) -> str:
    """Alias de 6 chars do subsistema. Cai no prefixo do nome se desconhecido."""
    if name in LOGGER_ALIAS:
        return LOGGER_ALIAS[name]
    for key, val in LOGGER_ALIAS.items():
        if name.startswith(key + "."):
            return val
    return name[:6].ljust(6)


class _ColoredFormatter(logging.Formatter):
    def __init__(self, cor: str | None = None):
        super().__init__()
        modo = (cor if cor is not None else _log_color).strip().lower()
        if modo == "always":
            self._color = True
        elif modo == "never":
            self._color = False
        else:  # auto — só colorido se o stderr for um TTY real
            self._color = sys.stderr.isatty()

    def _alias(self, name: str) -> str:
        return alias_for(name)

    def format(self, record: logging.LogRecord) -> str:
        ts    = self.formatTime(record, "%H:%M:%S")
        level = LEVEL_LABEL.get(record.levelno, record.levelname[:5])
        alias = self._alias(record.name)
        msg   = record.getMessage()
        # O contrato do `logging.Formatter`: `exc_text` pronto vale antes de
        # formatar `exc_info`. A redação de segredos (flow/utils/segredos_vivos)
        # entrega o traceback redigido em `exc_text` e anula `exc_info`; só
        # olhar `exc_info` fazia o console perder o traceback inteiro.
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            msg += "\n" + record.exc_text

        if self._color:
            c    = _LEVEL_COLOR.get(record.levelno, "")
            bold = _B if record.levelno >= logging.ERROR else ""
            colored_msg = f"{c}{msg}{_R}" if record.levelno >= logging.WARNING else msg
            return (
                f"{_DIM}{ts}{_R}  "
                f"{c}{bold}{level}{_R}  "
                f"{_DIM}{alias}{_R}  "
                f"{colored_msg}"
            )
        return f"{ts}  {level}  {alias}  {msg}"


# ── Estado do modulo ─────────────────────────────────────────────────────────

_configurado = False
_console: logging.Handler | None = None
_detached_console: logging.Handler | None = None
_catch_all: logging.Handler | None = None
# Handler filtrado de LOG_FILE_AGENT, guardado para poder ser removido quando o
# catch-all assumir o MESMO arquivo (senao cada linha sairia duplicada).
_agent_file: logging.Handler | None = None
_agent_file_path: str | None = None


def configure_logging() -> None:
    """Instala o root logger, o console e os arquivos opcionais. Idempotente.

    Le as variaveis AQUI, e nao no import: o `.env` do executor so entra no
    ambiente quando `executor.config` roda o `load_dotenv()`.
    """
    global _configurado, _console, _agent_file, _agent_file_path, _log_color
    if _configurado:
        return
    _configurado = True

    # Redação de segredos por padrão (DSN com senha, Bearer, Basic, PAT...) em
    # TODO registro do processo, antes de qualquer handler — o console, os
    # arquivos e o painel. O executor decifra DSN e monta cabeçalho de
    # autenticação, e logava tudo isso sem máscara; a lista é a mesma da API.
    from flow.utils.redacao_log import instalar_no_processo
    instalar_no_processo()

    _log_color = os.getenv("LOG_COLOR", "auto")

    plain = logging.Formatter(_LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(_nivel())

    # Console: todos os logs, sem filtro, com formatter colorido.
    _console = logging.StreamHandler()
    _console.setFormatter(_ColoredFormatter(_log_color))
    root.addHandler(_console)

    # Arquivo do executor: loggers executor.* e httpx (sem cores)
    agente = os.getenv("LOG_FILE_AGENT") or ""
    if agente:
        _agent_file = _rotating(agente)
        _agent_file.setFormatter(plain)
        _agent_file.addFilter(_PrefixFilter("executor", "httpx"))
        _agent_file_path = agente
        root.addHandler(_agent_file)

    # Arquivo do workflow: loggers flow.*, node.* e app.* (sem cores)
    workflow = os.getenv("LOG_FILE_WORKFLOW") or ""
    if workflow:
        h = _rotating(workflow)
        h.setFormatter(plain)
        h.addFilter(_PrefixFilter("flow", "node", "app"))
        root.addHandler(h)

    # Silenciar logs ruidosos do httpx (HTTP Request: GET/POST ...)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Avisos de validacao acumulados durante o import de config.py, que roda
    # antes deste ponto. Emitidos agora que existe para onde manda-los.
    try:
        from executor.config import flush_startup_warnings
        flush_startup_warnings()
    except Exception:  # pragma: no cover — config indisponivel (uso isolado)
        pass


def resolve_agent_log_path() -> str:
    """Caminho do arquivo de log do agente no modo painel.

    LOG_FILE_AGENT tem precedencia — quem ja configurou continua mandando no
    destino. Sem ele, o default deriva de EXECUTOR_LOG_DIR / ARTIFACTS_DIR,
    seguindo a mesma convencao de ~/AtlansExecutor usada pelos artefatos.
    """
    explicito = os.getenv("LOG_FILE_AGENT") or ""
    if explicito:
        return explicito

    from executor import config
    return str(pathlib.Path(config.LOG_DIR) / "executor.log")


def ensure_file_mirror() -> str:
    """Garante o handler rotativo CATCH-ALL — o espelho do console em disco.

    Idempotente: chamado na primeira vez que o painel liga e nunca desfeito. O
    arquivo continua recebendo tudo mesmo depois de o console voltar, seja pelo
    atalho de teclado ou pelo shutdown.

    Retorna o caminho efetivo. Levanta LoggingSetupError se nao conseguir
    abri-lo — quem chama DEVE abortar o painel nesse caso: ligar o dashboard
    sem o arquivo trocaria o log passo-a-passo por nada.
    """
    global _catch_all, _agent_file

    path = resolve_agent_log_path()
    if _catch_all is not None:
        return path

    root = logging.getLogger()

    # O handler filtrado de LOG_FILE_AGENT aponta para este mesmo arquivo? Sai
    # ANTES de o catch-all abrir: senao toda linha de `executor.*` sairia
    # duplicada, e dois RotatingFileHandler com o mesmo arquivo aberto brigam
    # na hora de rotacionar (no Windows, o rename de um arquivo aberto falha).
    if _agent_file is not None and _agent_file_path == path:
        root.removeHandler(_agent_file)
        _agent_file.close()
        _agent_file = None

    try:
        catch_all = _rotating(path)
    except OSError as exc:
        raise LoggingSetupError(f"Nao foi possivel abrir o log em '{path}': {exc}") from exc

    catch_all.setFormatter(logging.Formatter(_LOG_FORMAT))
    # Sem filtro, de proposito: este handler substitui o console, que tambem
    # nao tinha filtro. E o espelho do que ia para a tela.
    root.addHandler(catch_all)
    _catch_all = catch_all
    return path


def detach_console() -> None:
    """Tira o console do root — a tela fica livre para o painel. Idempotente."""
    global _detached_console
    if _console is None or _detached_console is not None:
        return
    logging.getLogger().removeHandler(_console)
    _detached_console = _console


def switch_to_dashboard_mode() -> str:
    """Liga o modo painel: garante o espelho em arquivo e libera a tela.

    Reversivel: `restore_console_mode()` traz o log de volta ao terminal sem
    fechar o arquivo, e uma nova chamada aqui devolve a tela ao painel. E o que
    sustenta a alternancia por teclado.
    """
    path = ensure_file_mirror()
    detach_console()
    return path


def restore_console_mode() -> None:
    """Reanexa o console. Idempotente — pode ser chamada de varios caminhos de
    saida (shutdown normal, atexit, KeyboardInterrupt) sem duplicar handlers.

    Os handlers de arquivo continuam onde estao: depois do painel fechar, o
    log segue sendo gravado ate o processo morrer.
    """
    global _detached_console
    if _detached_console is None:
        return
    root = logging.getLogger()
    if _detached_console not in root.handlers:
        root.addHandler(_detached_console)
    _detached_console = None


# ── Nivel de log em runtime ──────────────────────────────────────────────────
# Guarda o nivel configurado no boot para o toggle saber ao que voltar.
_nivel_base: int | None = None


def em_debug() -> bool:
    return logging.getLogger().level <= logging.DEBUG


def alternar_debug() -> bool:
    """Liga/desliga DEBUG sem reiniciar o executor. Retorna o estado novo.

    Diagnosticar um erro exigia parar o processo, editar LOG_LEVEL no .env e
    subir de novo — perdendo exatamente o estado que se queria investigar. Como
    nenhum handler tem nivel proprio (so o LogTailHandler, fixo em WARNING),
    mexer no root basta para o arquivo passar a receber DEBUG na hora.
    """
    global _nivel_base
    root = logging.getLogger()
    if _nivel_base is None:
        _nivel_base = root.level or logging.INFO

    if em_debug():
        root.setLevel(_nivel_base)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        return False

    root.setLevel(logging.DEBUG)
    # httpx/httpcore em DEBUG despejam cada frame HTTP e afogam o resto — o que
    # o operador quer ver e o `executor.*` e o `flow.*`. Ficam em INFO.
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    return True
