# app/models/workflow_run.py
from sqlalchemy import (
    Column, Integer, String, JSON, ForeignKey, DateTime, Text, Boolean, Float, Index, func, text,
)
from sqlalchemy.orm import relationship
from uuid import uuid4
from app.models.base import Base


class WorkflowRun(Base):
    __tablename__ = 'workflow_runs'
    __table_args__ = (
        Index('ix_wfrun_hash_status_time', 'workflow_hash', 'status', 'start_time'),
        # PERF: the most common History case is "my workspace, no status filter,
        # most recent first". With `status` in the MIDDLE of the composite index
        # (ix_wfrun_workspace_status_time), Postgres finds the workspace's rows
        # but cannot return them already sorted: it reads ALL of them and sorts
        # before applying the LIMIT 20. This prefix (workspace_id, start_time
        # DESC) is what makes the first page O(limit).
        Index('ix_wfrun_workspace_time', 'workspace_id', text('start_time DESC')),
        # PERF: the per-executor side panel filters by `host`, which had no index
        # at all — it was a full table scan on every opening.
        Index('ix_wfrun_host_time', 'host', text('start_time DESC')),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, default=lambda: str(uuid4()), nullable=False, index=True)
    flag_ative = Column(Boolean, default=True, nullable=False)

    task_id = Column(String(36), unique=True, nullable=False, index=True)
    workflow_hash = Column(String(36), ForeignKey('workflows.id_hash', ondelete='CASCADE'), nullable=False, index=True)
    # NOT NULL since 20260828_0001 — see the note on Workflow.workspace_id.
    # Written at dispatch and never changed: it is the tenant that actually
    # produced this run, even if the workflow is moved later.
    workspace_id = Column(String(36), nullable=False, index=True)
    schedule_id = Column(Integer, ForeignKey('schedules.id', ondelete='SET NULL'), nullable=True)

    status = Column(String, nullable=False, default='running', index=True)
    exit_code = Column(Integer, nullable=True)
    host = Column(String, nullable=True)
    # Policy tier at which the job was DELIVERED: "primary" | "fallback" |
    # "pool". Written together with `host` (INSERT and failover) — it is what
    # makes "ran on fallback/pool" observable per run, even if the workspace's
    # policy changes later. Null on runs predating the column.
    dispatch_tier = Column(String(8), nullable=True)
    # Trigger source and who triggered it (docs/specs/metrics-history.md §2):
    # "manual" | "retry" | "webhook" | "schedule". `triggered_by` is the user's
    # id_hash on authenticated routes; null for webhook and schedule. Runs
    # predating the column stay null — the screen shows "—".
    trigger_source = Column(String(16), nullable=True)
    triggered_by = Column(String(36), nullable=True)
    # Category of the error that closed the run: the flow taxonomy (user,
    # validation, timeout, resource, transient, internal) plus the server's
    # (no_executor, executor_lost, isolation, dispatch). It is what enables
    # "why does it fail" without a LIKE on `error_message`.
    error_category = Column(String(16), nullable=True)

    start_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    node_stats = Column(JSON, nullable=True)

    # PERF: lazy='raise' prevents accidental N+1 in listings (before: selectin loaded
    # Workflow+Schedule for EACH run → 101 queries to list 50 runs).
    # Endpoints that need it must use an explicit selectinload() in the query.
    workflow = relationship(
        'Workflow',
        back_populates='runs',
        primaryjoin='Workflow.id_hash==WorkflowRun.workflow_hash',
        lazy='raise',
    )
    schedule = relationship('Schedule', lazy='raise')
