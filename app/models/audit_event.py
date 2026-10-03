# app/models/audit_event.py
"""
Audit event model for tracking actions in the system.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, JSON, Index, func,
)
from app.models.base import Base


class AuditEvent(Base):
    """Audit record for relevant actions in the system."""
    __tablename__ = "audit_events"
    __table_args__ = (
        # PERF: ASC index — PostgreSQL does a backward scan automatically when it needs DESC.
        Index("ix_audit_timestamp", "timestamp"),
    )

    id            = Column(Integer, primary_key=True)
    workspace_id  = Column(String(36), nullable=False, index=True)
    user_id       = Column(String(36), nullable=True)
    action        = Column(String(64), nullable=False)
    resource_type = Column(String(64), nullable=True)
    resource_id   = Column(String(255), nullable=True)
    details       = Column(JSON, nullable=True)
    ip_address    = Column(String(45), nullable=True)
    user_agent    = Column(Text, nullable=True)
    timestamp     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
