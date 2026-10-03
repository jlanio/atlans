# app/models/workspace_member.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from uuid import uuid4
from app.models.base import Base


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    id          = Column(Integer, primary_key=True, index=True)
    id_hash     = Column(String(36), unique=True, default=lambda: str(uuid4()), nullable=False)
    workspace_id = Column(
        String(36),
        ForeignKey("workspaces.id_hash", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id     = Column(
        String(36),
        ForeignKey("users.id_hash", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # owner | admin | editor | viewer
    role        = Column(String(20), nullable=False, default="editor")
    invited_by  = Column(String(36), nullable=True)   # id_hash of whoever sent the invitation
    joined_at   = Column(DateTime, server_default=func.now(), nullable=False)
