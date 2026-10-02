# app/models/workspace_executor.py
from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, SmallInteger,
    String, UniqueConstraint, func,
)

from app.models.base import Base


class WorkspaceExecutor(Base):
    """Membro de um NÍVEL de executores dedicados de um workspace.

    tier 1 = principal; tier 2 = fallback (outros executores dedicados do
    próprio workspace). Um executor não pode estar nos dois níveis (UNIQUE).
    "Workspace isolado" não é um flag: é ter ≥1 linha em tier 1 com terminal
    efetivo `fail` — ver `workspace_executor_service`.
    """
    __tablename__ = "workspace_executors"
    __table_args__ = (
        UniqueConstraint("workspace_id", "executor_id", name="uq_workspace_executor"),
        CheckConstraint("tier IN (1, 2)", name="ck_workspace_executor_tier"),
        # Leitura quente do dispatch: os níveis de UM workspace.
        Index("ix_workspace_executors_ws_tier", "workspace_id", "tier"),
        # "Quais workspaces dependem deste executor?" — revogar/apagar um
        # executor consulta isto para bloquear o esvaziamento de um nível
        # principal. Nome explícito: é o que a migração e o bootstrap criam.
        Index("ix_workspace_executors_executor", "executor_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        String(36), ForeignKey("workspaces.id_hash", ondelete="CASCADE"),
        nullable=False,
    )
    executor_id = Column(
        String(36), ForeignKey("executors.id_hash", ondelete="CASCADE"),
        nullable=False,
    )
    tier = Column(SmallInteger, nullable=False)
    added_by = Column(String(36), nullable=True)   # User.id_hash (auditoria)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
