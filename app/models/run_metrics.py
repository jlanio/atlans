# app/models/run_metrics.py
"""
Modelos de metricas de execucao para billing, performance e observabilidade.
"""
from sqlalchemy import (
    Column, Integer, String, Float, BigInteger, Boolean, Text,
    DateTime, JSON, Date, Index, UniqueConstraint, func,
)
from app.models.base import Base


class WorkflowRunMetrics(Base):
    """Metricas agregadas por execucao de workflow."""
    __tablename__ = "workflow_run_metrics"
    __table_args__ = (
        Index("ix_run_metrics_workspace", "workspace_id", "started_at"),
        Index("ix_run_metrics_workflow", "workflow_hash", "started_at"),
        # Indice SQL "ix_run_metrics_executor" (renomeado em 20260716_0001).
        # Referencia colunas pelo nome SQL — nao pelo atributo Python.
        Index("ix_run_metrics_executor", "executor_id", "started_at"),
    )

    id              = Column(Integer, primary_key=True)
    run_id          = Column(String(36), unique=True, nullable=False, index=True)
    workflow_hash   = Column(String(36), nullable=False)
    workspace_id    = Column(String(36), nullable=False)
    # Colunas SQL "executor_id/name/ip" (renomeadas em 20260716_0001);
    # atributos Python mantidos como agent_* ate R2.3.
    executor_id        = Column("executor_id", String(36), nullable=True)
    executor_name      = Column("executor_name", String(100), nullable=True)
    executor_ip        = Column("executor_ip", String(45), nullable=True)
    user_id         = Column(String(36), nullable=True)

    # Timing
    started_at      = Column(DateTime(timezone=True), nullable=False)
    ended_at        = Column(DateTime(timezone=True), nullable=True)
    duration_ms     = Column(Float, nullable=True)

    # Recursos computacionais
    cpu_avg_pct     = Column(Float, nullable=True)
    cpu_peak_pct    = Column(Float, nullable=True)
    mem_avg_mb      = Column(Float, nullable=True)
    mem_peak_mb     = Column(Float, nullable=True)

    # Dados processados
    input_bytes     = Column(BigInteger, default=0)
    output_bytes    = Column(BigInteger, default=0)
    transfer_bytes  = Column(BigInteger, default=0)
    total_features  = Column(Integer, default=0)

    # Operacoes
    nodes_executed  = Column(Integer, default=0)
    nodes_failed    = Column(Integer, default=0)
    nodes_cached    = Column(Integer, default=0)
    operation_types = Column(JSON, nullable=True)  # {"buffer": 2, "intersect": 1}

    # Contexto espacial
    spatial_summary = Column(JSON, nullable=True)  # {crs: [...], bbox: [...], geometry_types: [...]}

    # Status
    status          = Column(String(16), nullable=False)
    error_type      = Column(String(64), nullable=True)
    error_node_id   = Column(String(255), nullable=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())


class NodeRunMetrics(Base):
    """Metricas por no executado dentro de um run."""
    __tablename__ = "node_run_metrics"
    __table_args__ = (
        Index("ix_node_metrics_run", "run_id"),
        Index("ix_node_metrics_name", "node_name", "started_at"),
    )

    id              = Column(Integer, primary_key=True)
    run_id          = Column(String(36), nullable=False)
    node_id         = Column(String(255), nullable=False)
    node_name       = Column(String(255), nullable=False)
    node_type       = Column(String(32), nullable=True)

    # Timing
    started_at      = Column(DateTime(timezone=True), nullable=True)
    duration_ms     = Column(Float, nullable=True)

    # Recursos
    cpu_avg_pct     = Column(Float, nullable=True)
    mem_peak_mb     = Column(Float, nullable=True)

    # Dados
    input_bytes     = Column(BigInteger, default=0)
    output_bytes    = Column(BigInteger, default=0)
    input_features  = Column(Integer, nullable=True)
    output_features = Column(Integer, nullable=True)

    # Espacial
    geometry_type   = Column(String(32), nullable=True)
    crs             = Column(String(32), nullable=True)
    bbox            = Column(JSON, nullable=True)
    vertex_count    = Column(Integer, nullable=True)

    # Status
    status          = Column(String(16), nullable=False)
    cache_hit       = Column(Boolean, default=False)
    error_message   = Column(Text, nullable=True)


class UsageDaily(Base):
    """Agregacao diaria de uso por workspace (base para billing)."""
    __tablename__ = "usage_daily"
    __table_args__ = (
        UniqueConstraint("date", "workspace_id", name="uq_usage_daily"),
        Index("ix_usage_daily_ws", "workspace_id", "date"),
    )

    id                    = Column(Integer, primary_key=True)
    date                  = Column(Date, nullable=False)
    workspace_id          = Column(String(36), nullable=False)

    total_runs            = Column(Integer, default=0)
    successful_runs       = Column(Integer, default=0)
    failed_runs           = Column(Integer, default=0)

    total_cpu_seconds     = Column(Float, default=0)
    total_mem_mb_seconds  = Column(Float, default=0)
    total_duration_ms     = Column(Float, default=0)
    total_input_bytes     = Column(BigInteger, default=0)
    total_output_bytes    = Column(BigInteger, default=0)
    total_transfer_bytes  = Column(BigInteger, default=0)
    total_features        = Column(BigInteger, default=0)

    total_nodes_executed  = Column(Integer, default=0)
    operation_breakdown   = Column(JSON, nullable=True)
