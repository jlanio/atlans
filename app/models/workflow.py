# app/models/workflow.py
from sqlalchemy import (
    Column, Integer, String, JSON, ForeignKey, DateTime, Text, Boolean, Index, func, text,
)
from sqlalchemy.orm import relationship
from uuid import uuid4
from app.models.base import Base


class Workflow(Base):
    __tablename__ = 'workflows'
    __table_args__ = (
        Index('ix_workflow_workspace_active', 'workspace_id', 'flag_ative'),
        # PARTIAL: the name is only unique among LIVE workflows. Delete is soft
        # (soft_delete_by_hash keeps the row and writes deleted_at), so a full
        # constraint left the name of everything deleted taken forever — and
        # invisibly, since no listing shows soft-deleted ones. Duplicating,
        # creating and renaming hit that wall.
        #
        # The index name repeats the previous constraint's on purpose:
        # workflow_service and workflow_move_service recognize the collision by
        # `"uq_workflow_name_workspace" in str(exc.orig)`.
        # `sqlite_where` alongside `postgresql_where`: the tests build the schema
        # with `metadata.create_all` on SQLite, and a dialect that ignores the
        # predicate creates a FULL unique index — the opposite of what this
        # index means. Without both, a test of the partial semantics would pass
        # in production and fail in the suite (or worse, the reverse).
        Index(
            'uq_workflow_name_workspace', 'name', 'workspace_id',
            unique=True,
            postgresql_where=text('deleted_at IS NULL'),
            sqlite_where=text('deleted_at IS NULL'),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, default=lambda: str(uuid4()), nullable=False, index=True)
    flag_ative = Column(Boolean, default=True, nullable=False)

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String, nullable=True)
    priority = Column(Integer, default=0)
    # NOT NULL since 20260828_0001: while the column accepted NULL, the tenant
    # filters carried an `OR workspace_id IS NULL` that made the row visible
    # to ANY authenticated user.
    workspace_id = Column(String(36), nullable=False, index=True)
    group_id = Column(String(36), ForeignKey('workflow_groups.id_hash', ondelete='SET NULL'), nullable=True, index=True)
    params_schema = Column(JSON, nullable=True)
    notification_url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by_id = Column(String(36), nullable=True)
    updated_by_id = Column(String(36), nullable=True)

    # The workflow's provenance, not a privilege: "usuario" (the default) or
    # "assistente" (created by the Home assistant, hidden from listings by
    # default). Some day it absorbs "importado"/"template"/"duplicado"; hence
    # VARCHAR and not Boolean. NOT NULL with server_default: every existing
    # workflow becomes "usuario" without a backfill.
    origem = Column(String(16), nullable=False, server_default=text("'usuario'"))

    definition = Column(JSON, nullable=False)
    pinned_outputs = Column(JSON, nullable=True)
    pin_metadata = Column(JSON, nullable=True)

    portal_access = Column(String(16), nullable=False, server_default="disabled")
    portal_shared_with = Column(JSON, nullable=True)
    deleted_at = Column(DateTime, nullable=True, default=None)

    group = relationship('WorkflowGroup', back_populates='workflows', foreign_keys=[group_id])
    schedules = relationship("Schedule", back_populates="workflow", cascade="all, delete-orphan")
    runs = relationship('WorkflowRun', back_populates='workflow', cascade='all, delete')
    versions = relationship('WorkflowVersion', back_populates='workflow', cascade='all, delete-orphan', order_by='WorkflowVersion.version_number')
