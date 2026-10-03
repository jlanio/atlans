# app/models/conversa.py
"""
Home assistant conversations — persisted in the database, several per person, no expiry.

Unlike the editor assistant, whose transcript lives in Redis with a 24h TTL
(`app/services/assistente_service.py`), Home keeps the conversation FOR REAL:
the person reopens the page days later and the conversation is there. Two
tables:

- `conversas`: one row per conversation (owner, title, optional workflow
  context, origin, total tokens spent, dates). `deleted_at` is a soft delete —
  deleting removes it from the list without losing the actual history.
- `mensagens`: the messages in order. `blocos` stores the content VERBATIM in
  the project's format (a string OR a list of `thinking`/`text`/`tool_use`/
  `tool_result` blocks — see `app/services/openrouter.py`), because that is
  what the loop resends when resuming the conversation — including the
  reasoning block's `reasoning_details`, which the provider needs to receive
  back. `uso` and `meta` are optional.

The foreign key from `mensagens` to `conversas` is by `id_hash` (the public,
unique hash), with CASCADE: deleting a conversation FOR REAL takes the messages
with it. The normal path, however, is the soft delete, which does not cascade.
"""
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)

from app.models.base import Base


class Conversa(Base):
    __tablename__ = "conversas"

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid4()))
    # The owner's User.id_hash. CASCADE only on the user's hard delete; the
    # account's soft delete does not delete conversations (the history stays),
    # and the conversation has its own.
    user_id = Column(String(36), ForeignKey("users.id_hash", ondelete="CASCADE"), nullable=False, index=True)
    # Preferred workspace at the time of the conversation (optional) and CONTEXT
    # workflow (optional) — not the assistant's workflow, just the reference
    # the person opened.
    workspace_id = Column(String(36), nullable=True)
    workflow_id = Column(String(36), nullable=True)
    titulo = Column(String(120), nullable=True)
    # "home" today; the column exists for the day the editor also persists here.
    origem = Column(String(16), nullable=False, server_default=text("'home'"))
    tokens_total = Column(Integer, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    # Stamped by the service on every turn — it is what the "my conversations"
    # list sorts by (the most recently active on top).
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_conversas_user_updated", "user_id", "updated_at"),
    )


class Mensagem(Base):
    __tablename__ = "mensagens"

    id = Column(Integer, primary_key=True, index=True)
    conversa_id = Column(
        String(36), ForeignKey("conversas.id_hash", ondelete="CASCADE"), nullable=False, index=True
    )
    # The order is the message's stable index in the conversation: replay reads
    # it in ascending order, and it is what `anexar` increments (max+1).
    ordem = Column(Integer, nullable=False)
    papel = Column(String(16), nullable=False)  # "user" | "assistant"
    # VERBATIM: a string OR a list of blocks, in the project's format (plain
    # dicts, as the loop stores them). Translating for the wire is the model
    # client's job.
    blocos = Column(JSON, nullable=False)
    uso = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("conversa_id", "ordem", name="uq_mensagens_conversa_ordem"),
    )
