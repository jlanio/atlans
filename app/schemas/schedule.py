from pydantic import BaseModel, Field, validator
from typing import Any, Dict, Optional, Literal
from datetime import datetime

from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO


class ScheduleNotice(BaseModel):
    """Warning about what HAPPENED (or not) to the schedule on save.

    Mirrors `WorkflowMoveWarning`: saving the workflow never fails because of
    the schedule (the exception is best-effort and swallowed by the caller), so
    what the user needs to know — "the schedule was not applied because the
    workflow is inactive", "the expression is invalid and the previous schedule
    was kept" — comes back here, ready to become a toast, instead of dying in
    the log.
    """
    code: str = Field(..., description="Identificador estável do tipo de aviso.")
    severity: Literal["warning", "info"] = "warning"
    message: str = Field(..., description="Texto em pt-BR pronto para exibir.")
    details: Dict[str, Any] = Field(default_factory=dict)


class ScheduleBase(BaseModel):
    strategy: str = Field(..., description="Strategy: 'cron', 'interval', or 'rrule'")
    interval: Optional[int] = Field(None, description="Interval count (strategy='interval')")
    unit: Optional[str] = Field(None, description="Unit: seconds, minutes, hours, days (strategy='interval')")
    cron_expression: Optional[str] = Field(None, description="Cron expression (strategy='cron', format: 'min hour day month dow')")
    rrule_expression: Optional[str] = Field(
        None,
        description="RFC 5545 RRULE for calendar scheduling, e.g. 'FREQ=MONTHLY;BYDAY=MO;BYSETPOS=1' (strategy='rrule')"
    )
    # It used to be `America/Cuiaba` — same offset as what the `ScheduleTrigger`
    # node sends, different name. Two names for the same intent is how the
    # third value (UTC, in the scheduler) went unnoticed for so long.
    timezone: str = Field(
        FUSO_PADRAO_DO_AGENDAMENTO, description="Timezone for scheduling"
    )
    active: bool = Field(True, description="Whether the schedule is active")
    workspace_id: Optional[str] = Field(None, description="ID do workspace/tenant")


class ScheduleCreate(ScheduleBase):
    """Schema for creating a new schedule"""
    pass


class ScheduleRead(ScheduleBase):
    """Schema for reading schedule data"""
    id: int
    id_hash: str
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    retry_count: int
    job_id: str

    class Config:
        from_attributes = True


class ScheduleUpdate(BaseModel):
    """
    Schema for updating a schedule.
    All fields are optional — include only the ones you want to change.
    """
    strategy: Optional[Literal['cron', 'interval', 'rrule']] = Field(None, description="Strategy: 'cron', 'interval', ou 'rrule'")
    interval: Optional[int] = Field(None, description="Quantidade para intervalo (strategy='interval')")
    unit: Optional[Literal['seconds', 'minutes', 'hours', 'days']] = Field(None, description="Unidade para intervalo (strategy='interval')")
    cron_expression: Optional[str] = Field(None, description="Expressão cron (strategy='cron', formato: 'min hour day month dow')")
    rrule_expression: Optional[str] = Field(None, description="RRULE RFC 5545 (strategy='rrule')")
    timezone: Optional[str] = Field(None, description="Timezone para agendamento")
    active: Optional[bool] = Field(None, description="Se o agendamento deve estar ativo ou não")
    workspace_id: Optional[str] = Field(None, description="ID do workspace/tenant")

    @validator('interval', always=True)
    def check_interval_if_needed(cls, v, values):
        if values.get('strategy') == 'interval' and v is None:
            raise ValueError('interval é obrigatório quando strategy="interval"')
        return v

    @validator('unit', always=True)
    def check_unit_if_needed(cls, v, values):
        if values.get('strategy') == 'interval' and v is None:
            raise ValueError('unit é obrigatório quando strategy="interval"')
        return v

    @validator('cron_expression', always=True)
    def check_cron_if_needed(cls, v, values):
        if values.get('strategy') == 'cron' and not v:
            raise ValueError('cron_expression é obrigatório quando strategy="cron"')
        return v

    @validator('rrule_expression', always=True)
    def check_rrule_if_needed(cls, v, values):
        if values.get('strategy') == 'rrule' and not v:
            raise ValueError('rrule_expression é obrigatório quando strategy="rrule"')
        return v