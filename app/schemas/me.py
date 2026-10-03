# app/schemas/me.py
"""Schemas for the "Meu" ("Mine") scope — per-PERSON slices, across all their
workspaces. Today only schedules (Home's "Meu → Agendamentos" panel)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MySchedule(BaseModel):
    """A schedule in the person's list. One per row (not one per workflow, as in
    the Projects summary): the same routine may have more than one.

    A null `next_run_at` has two meanings the web app tells apart by `active`:
    paused (the scheduler does not compute the next one for inactive ones) or
    just created (the scheduler fills it in within 30 s). "Paused" also has two
    causes — the schedule's own `active` or the workflow's `flag_ative` being
    off —, which is why the two fields come together.
    """
    job_id: str
    id_hash: str
    active: bool
    strategy: str
    cron_expression: Optional[str] = None
    interval: Optional[int] = None
    unit: Optional[str] = None
    rrule_expression: Optional[str] = None
    timezone: Optional[str] = None
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    retry_count: int = 0
    workflow_id: str
    workflow_name: str
    flag_ative: bool
    workspace_id: Optional[str] = None
    # The workflow's provenance (usuario|assistente), for the "assistente" badge
    # on the Home panel. It comes from the JOIN with Workflow (column from the
    # origin PR); default "usuario" because every new schema field has a default.
    origem: str = "usuario"
