# flow/utils/logger.py
"""
Logger for the flow module — independent of app/.
Uses standard Python logging; handlers configured by executor/main.

Every logger here carries the secret redaction filter (`redacao_log`): flow
also runs inside the API (validation, node simulation), and there is no
LogRecord factory there like the one the executor installs.
"""
import logging

from flow.utils.redacao_log import SecretScrubFilter

_scrub_filter = SecretScrubFilter()


def get_logger(name: str) -> logging.Logger:
    """Retorna logger configurado para o modulo flow."""
    logger = logging.getLogger(name)
    if _scrub_filter not in logger.filters:
        logger.addFilter(_scrub_filter)
    return logger
