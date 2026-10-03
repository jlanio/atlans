# app/models/workflow_group.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from uuid import uuid4
from app.models.base import Base


class WorkflowGroup(Base):
    __tablename__ = 'workflow_groups'

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, default=lambda: str(uuid4()), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    workspace_id = Column(String(36), nullable=True, index=True)

    # Order chosen by hand on the Projects screen. Without it the GET had no
    # `order_by` at all: the order came undefined from the database and could
    # change between two loads of the same page.
    position = Column(Integer, default=0, server_default="0", nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    workflows = relationship('Workflow', back_populates='group', foreign_keys='Workflow.group_id')
