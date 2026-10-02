# app/models/models.py
"""
Re-exporta modelos para retrocompatibilidade.
Novos imports devem usar os modulos individuais:
  from app.models.workflow import Workflow
  from app.models.workflow_run import WorkflowRun
  from app.models.schedule import Schedule
  from app.models.workflow_version import WorkflowVersion
  from app.models.workflow_group import WorkflowGroup
"""
from app.models.workflow_group import WorkflowGroup
from app.models.workflow import Workflow
from app.models.schedule import Schedule
from app.models.workflow_run import WorkflowRun
from app.models.workflow_version import WorkflowVersion

__all__ = [
    "WorkflowGroup",
    "Workflow",
    "Schedule",
    "WorkflowRun",
    "WorkflowVersion",
]
