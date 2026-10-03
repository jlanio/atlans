# app/models/schedule.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from uuid import uuid4
from app.models.base import Base


class Schedule(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, default=lambda: str(uuid4()), nullable=False, index=True)

    workflow_hash = Column(String(36), ForeignKey('workflows.id_hash', ondelete='CASCADE'), nullable=False, index=True)
    strategy = Column(String, nullable=False)
    interval = Column(Integer, nullable=True)
    unit = Column(String, nullable=True)
    cron_expression = Column(String, nullable=True)
    rrule_expression = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    workspace_id = Column(String(36), nullable=True, index=True)

    next_run_at = Column(DateTime, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    job_id = Column(String, unique=True, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    # PERF: lazy='raise' prevents accidental N+1 — the same treatment already
    # applied to WorkflowRun.workflow. With 'selectin', EVERY `select(Schedule)`
    # fired a second SELECT on workflows bringing the `definition` column
    # (full JSON) of every referenced workflow. The scheduler runs every 30s
    # on 4 workers and never reads this relationship — it was pure traffic.
    # Endpoints that need it must use an explicit selectinload() in the query.
    workflow = relationship('Workflow', back_populates='schedules', lazy='raise')
