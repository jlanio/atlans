# app/models/user_executor_assignment.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from uuid import uuid4
from app.models.base import Base


class UserExecutorAssignment(Base):
    __tablename__ = "user_executor_assignments"
    __table_args__ = (
        # Constraint referencia colunas pelo nome SQL (executor_id), nao pelo
        # atributo Python (executor_id ate R2.3).
        UniqueConstraint("user_id", "executor_id", name="uq_user_executor"),
    )

    id          = Column(Integer, primary_key=True, index=True)
    id_hash     = Column(String(36), unique=True, default=lambda: str(uuid4()), nullable=False)
    user_id     = Column(
        String(36),
        ForeignKey("users.id_hash", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nome SQL "executor_id" (renomeada em 20260716_0001); atributo Python
    # mantido como executor_id ate R2.3 renomear identificadores.
    executor_id    = Column(
        "executor_id",
        String(36),
        ForeignKey("executors.id_hash", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by = Column(String(36), nullable=True)   # id_hash do admin que atribuiu
    assigned_at = Column(DateTime, server_default=func.now(), nullable=False)
