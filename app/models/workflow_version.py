# app/models/workflow_version.py
from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class WorkflowVersion(Base):
    __tablename__ = 'workflow_versions'
    __table_args__ = (
        UniqueConstraint('workflow_hash', 'version_number', name='uq_workflow_version'),
    )

    id = Column(Integer, primary_key=True, index=True)
    workflow_hash = Column(
        String(36),
        ForeignKey('workflows.id_hash', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    definition = Column(JSON, nullable=False)
    change_note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    workflow = relationship('Workflow', back_populates='versions')
