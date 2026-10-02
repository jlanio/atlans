import logging
from logging.handlers import RotatingFileHandler
import os

# ── Secret scrubbing ─────────────────────────────────────────────────────────
# Os padrões e o filtro moram em `flow/utils/redacao_log.py` — o flow está nas
# três imagens, e o executor precisa da MESMA lista. Reexportados com os nomes
# de sempre para os chamadores do app.
from flow.utils.redacao_log import (  # noqa: F401
    _REDACTED,
    _SCRUB_PATTERNS,
    SecretScrubFilter,
    _scrub,
    scrub_text,
)


_secret_filter = SecretScrubFilter()

# Configurações baseadas em variáveis de ambiente
# LOG_LEVEL define o nível mínimo de log para toda a aplicação
# Pode ser 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "app.log")
# Define o tamanho máximo do arquivo de log antes de rotacionar (10MB)
MAX_LOG_BYTES = 10 * 1024 * 1024
# Define quantos arquivos de backup manter
BACKUP_COUNT = 5

# Formato do log: timestamp, nível, nome do logger/módulo, mensagem e, opcionalmente, traceback de exceções
LOG_FORMAT = "%(asctime)s — %(levelname)s — %(name)s — %(message)s"
# Um formato mais detalhado que inclui o traceback para níveis de erro e crítico
LOG_FORMAT_DETAILED = "%(asctime)s — %(levelname)s — %(name)s — %(message)s%(exc_info)s"


def get_logger(name: str) -> logging.Logger:
    """
    Cria ou retorna um Logger configurado com handlers de console e arquivo.

    Args:
        name: O nome do logger (geralmente __name__ do módulo).
    Returns:
        Uma instância do logger configurada.
    """
    # Obtém um logger existente ou cria um novo com o nome especificado
    logger = logging.getLogger(name)

    # Se o logger já possui handlers, significa que já foi configurado
    # e podemos retorná-lo para evitar duplicação de handlers.
    if logger.handlers:
        # Garante que o scrub filter esta presente mesmo em loggers
        # ja configurados (defesa em profundidade — nao duplica).
        if _secret_filter not in logger.filters:
            logger.addFilter(_secret_filter)
        return logger

    # O nível é o global, definido pela variável de ambiente LOG_LEVEL.
    logger.setLevel(LOG_LEVEL)

    # Anexa filtro de scrub antes de qualquer handler processar registros —
    # garante que mesmo se o log propagar pro root, o record ja esta redigido.
    logger.addFilter(_secret_filter)

    # Se o root logger já tem handlers configurados (ex: ao rodar no executor,
    # que configura o root em executor/main.py), propaga para ele em vez de criar
    # um handler de console próprio — evita formato duplicado/inconsistente.
    root = logging.getLogger()
    if root.handlers:
        logger.propagate = True
        return logger

    logger.propagate = False  # evita duplicação quando o root não está configurado

    # --- Configuração do Handler de Console (para exibir logs no terminal) ---
    ch = logging.StreamHandler()
    # O nível do handler determina quais logs ele irá processar *depois* que o logger os filtrou
    ch.setLevel(LOG_LEVEL)
    # Define o formato para o console
    ch.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(ch)

    # --- Configuração do Handler de Arquivo Rotativo (para salvar logs em arquivo) ---
    # Cria o diretório para o arquivo de log se ele não existir
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    fh = RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT)
    # O nível do handler de arquivo também segue o nível do logger
    fh.setLevel(LOG_LEVEL)
    # Define o formato para o arquivo. Usamos o formato detalhado para incluir exceções no arquivo.
    fh.setFormatter(logging.Formatter(LOG_FORMAT_DETAILED))
    logger.addHandler(fh)

    # Mensagem de configuração inicial
    if logger.level <= logging.DEBUG:
        logger.info(f"Logger '{name}' configured with level {logging.getLevelName(logger.level)}")

    # Reduz verbosidade de SQLAlchemy
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    return logger