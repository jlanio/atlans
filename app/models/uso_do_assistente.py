# app/models/uso_do_assistente.py
"""What each turn of the assistant consumed — and cost.

One row per TURN of the loop, not per conversation: that is where the quota is
already charged, the two never diverge, and a conversation abandoned midway has
already recorded what it spent up to that point. Summing only at the end would
lose those, and lose them on the LOW side — the wrong side to err on in a cost
table.

**No content lives here.** Counts, the model and the cost. What this table
answers is how much the bill was, not what was said.

Contract in docs/editor-assistant.md.
"""
from uuid import uuid4

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String, func, text

from app.models.base import Base


class AssistantUsage(Base):
    __tablename__ = "uso_do_assistente"
    __table_args__ = (
        # The table's two questions: how much this person consumes per day, and
        # how much came in over the window of the last 30 days.
        Index("ix_uso_do_assistente_user", "user_id", "created_at"),
        Index("ix_uso_do_assistente_quando", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, nullable=False,
                     default=lambda: str(uuid4()))

    user_id = Column(String(36), nullable=False)   # users.id_hash

    # The model this turn was produced WITH, stored and not inferred: on the
    # day someone switches the model, the history must keep saying which one
    # it was made with, otherwise comparing before and after becomes
    # impossible right at the first switch.
    modelo = Column(String(120), nullable=False)
    superficie = Column(String(24), nullable=True)   # home | editor

    # `entrada` ALREADY INCLUDES what came from the cache, and `raciocinio` is a
    # slice of `saida` — it is the same convention as `assistente_service.Uso`,
    # kept on purpose so nobody needs to convert anything when reading.
    entrada = Column(Integer, nullable=False, server_default=text("0"))
    saida = Column(Integer, nullable=False, server_default=text("0"))
    cache_leitura = Column(Integer, nullable=False, server_default=text("0"))
    raciocinio = Column(Integer, nullable=False, server_default=text("0"))

    # What the provider said it cost. NUMERIC and not FLOAT: these are sums of
    # money over thousands of rows, and binary rounding shows up in the total.
    # It is the REAL cost — repricing with another model uses the counts.
    custo_usd = Column(Numeric(12, 6), nullable=False, server_default=text("0"))

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
