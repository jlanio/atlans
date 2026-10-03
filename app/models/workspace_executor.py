# app/models/workspace_executor.py
from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, SmallInteger,
    String, UniqueConstraint, func,
)

from app.models.base import Base


class WorkspaceExecutor(Base):
    """Member of a TIER of a workspace's dedicated executors.

    tier 1 = primary; tier 2 = fallback (other dedicated executors of the
    workspace itself). An executor cannot be in both tiers (UNIQUE).
    "Isolated workspace" is not a flag: it is having ≥1 row in tier 1 with an
    effective terminal of `fail` — see `workspace_executor_service`.
    """
    __tablename__ = "workspace_executors"
    __table_args__ = (
        UniqueConstraint("workspace_id", "executor_id", name="uq_workspace_executor"),
        CheckConstraint("tier IN (1, 2)", name="ck_workspace_executor_tier"),
        # Hot read in dispatch: the tiers of ONE workspace.
        Index("ix_workspace_executors_ws_tier", "workspace_id", "tier"),
        # "Which workspaces depend on this executor?" — revoking/deleting an
        # executor queries this to block emptying a primary tier. Explicit
        # name: it is what the migration and the bootstrap create.
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
