# flow/utils/logger.py
"""
Logger do modulo flow — independente de app/.
Usa logging padrao do Python; handlers configurados pelo executor/main.

Todo logger daqui leva o filtro de redação de segredos (`redacao_log`): o flow
também roda dentro da API (validação, simulação de nó), e lá não há a fábrica
de LogRecord que o executor instala.
"""
import logging

from flow.utils.redacao_log import SecretScrubFilter

_filtro = SecretScrubFilter()


def get_logger(name: str) -> logging.Logger:
    """Retorna logger configurado para o modulo flow."""
    logger = logging.getLogger(name)
    if _filtro not in logger.filters:
        logger.addFilter(_filtro)
    return logger
