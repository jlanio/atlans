import logging
from logging.handlers import RotatingFileHandler
import os

# ── Secret scrubbing ─────────────────────────────────────────────────────────
# The patterns and the filter live in `flow/utils/redacao_log.py` — flow is in
# all three images, and the executor needs the SAME list. Re-exported under the
# usual names for the app's callers.
from flow.utils.redacao_log import (  # noqa: F401
    _REDACTED,
    _SCRUB_PATTERNS,
    SecretScrubFilter,
    _scrub,
    scrub_text,
)


_secret_filter = SecretScrubFilter()

# Settings based on environment variables
# LOG_LEVEL sets the minimum log level for the whole application
# Can be 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "app.log")
# Sets the maximum log file size before rotating (10MB)
MAX_LOG_BYTES = 10 * 1024 * 1024
# Define quantos arquivos de backup manter
BACKUP_COUNT = 5

# Log format: timestamp, level, logger/module name, message and, optionally, exception tracebacks
LOG_FORMAT = "%(asctime)s — %(levelname)s — %(name)s — %(message)s"
# A more detailed format that includes the traceback for error and critical levels
LOG_FORMAT_DETAILED = "%(asctime)s — %(levelname)s — %(name)s — %(message)s%(exc_info)s"


def get_logger(name: str) -> logging.Logger:
    """
    Creates or returns a Logger configured with console and file handlers.

    Args:
        name: The logger name (usually the module's __name__).
    Returns:
        A configured logger instance.
    """
    # Gets an existing logger or creates a new one with the given name
    logger = logging.getLogger(name)

    # If the logger already has handlers, it has already been configured
    # and we can return it to avoid duplicate handlers.
    if logger.handlers:
        # Ensures the scrub filter is present even on loggers
        # already configured (defense in depth — does not duplicate).
        if _secret_filter not in logger.filters:
            logger.addFilter(_secret_filter)
        return logger

    # The level is the global one, set by the LOG_LEVEL environment variable.
    logger.setLevel(LOG_LEVEL)

    # Attaches the scrub filter before any handler processes records —
    # ensures that even if the log propagates to root, the record is already redacted.
    logger.addFilter(_secret_filter)

    # If the root logger already has handlers configured (e.g., when running in the
    # executor, which configures root in executor/main.py), propagates to it instead
    # of creating its own console handler — avoids duplicate/inconsistent format.
    root = logging.getLogger()
    if root.handlers:
        logger.propagate = True
        return logger

    logger.propagate = False  # avoids duplication when root is not configured

    # --- Console Handler setup (to show logs in the terminal) ---
    ch = logging.StreamHandler()
    # The handler's level determines which logs it will process *after* the logger has filtered them
    ch.setLevel(LOG_LEVEL)
    # Define o formato para o console
    ch.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(ch)

    # --- Rotating File Handler setup (to save logs to a file) ---
    # Creates the directory for the log file if it does not exist
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    fh = RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT)
    # The file handler's level also follows the logger's level
    fh.setLevel(LOG_LEVEL)
    # Sets the format for the file. We use the detailed format to include exceptions in the file.
    fh.setFormatter(logging.Formatter(LOG_FORMAT_DETAILED))
    logger.addHandler(fh)

    # Initial setup message
    if logger.level <= logging.DEBUG:
        logger.info(f"Logger '{name}' configured with level {logging.getLevelName(logger.level)}")

    # Reduces SQLAlchemy verbosity
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    return logger