"""Helpers de datetime — evitam o deprecated `datetime.utcnow()` do Python 3.12+.

Contexto: `datetime.utcnow()` foi deprecado na 3.12 e será removido em versões
futuras. O substituto oficial é `datetime.now(timezone.utc)`, que retorna um
datetime timezone-aware.

Porém, muitas colunas SQLAlchemy do projeto são `DateTime` (sem `timezone=True`)
e esperam valores naive. Para preservar esse contrato, `utc_now_naive()` remove
o tzinfo antes de retornar.
"""
from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """Retorna datetime UTC naive (sem tzinfo).

    Substituto drop-in para `datetime.utcnow()` — compatível com colunas
    SQLAlchemy DateTime sem timezone. Preserva o comportamento histórico
    do projeto.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
