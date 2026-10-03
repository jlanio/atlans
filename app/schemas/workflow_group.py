from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WorkflowGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    workspace_id: Optional[str] = None
    workflow_ids: List[str] = Field(default_factory=list)


class WorkflowGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    workflow_ids: Optional[List[str]] = None


class WorkflowGroupReorder(BaseModel):
    """New order of the groups, from the first position to the last.

    The position comes from the list's INDEX, not from a number sent by the
    client: that way there is no intermediate state with two equal positions,
    and nothing is left for the client to make up the numbering.
    """
    group_ids: List[str] = Field(..., min_length=1)


class WorkflowGroupRead(BaseModel):
    id: int
    id_hash: str
    name: str
    description: Optional[str]
    workspace_id: Optional[str]
    position: int = 0
    # All non-deleted workflows in the group (inactive ones included) — it is
    # what the Projects screen shows, and an inactive one stays in the list.
    # Counting only the active ones made "3 workflows" turn into "2" when one
    # was deactivated.
    workflow_count: int = 0
    # Only those with `flag_ative`; the screen shows "3 workflows · 2 ativos".
    active_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
