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
        # PERF: o caso mais comum do Historico e "meu workspace, sem filtro de
        # status, mais recentes primeiro". Com `status` no MEIO do indice
        # composto (ix_wfrun_workspace_status_time), o Postgres acha as linhas do
        # workspace mas nao consegue devolve-las ja ordenadas: le TODAS e ordena
        # antes de aplicar o LIMIT 20. Este prefixo (workspace_id, start_time
        # DESC) e o que torna a primeira pagina O(limit).
        Index('ix_wfrun_workspace_time', 'workspace_id', text('start_time DESC')),
        # PERF: o painel lateral por executor filtra por `host`, que nao tinha
        # indice nenhum — era scan da tabela inteira a cada abertura.
        Index('ix_wfrun_host_time', 'host', text('start_time DESC')),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, default=lambda: str(uuid4()), nullable=False, index=True)
    flag_ative = Column(Boolean, default=True, nullable=False)

    task_id = Column(String(36), unique=True, nullable=False, index=True)
    workflow_hash = Column(String(36), ForeignKey('workflows.id_hash', ondelete='CASCADE'), nullable=False, index=True)
    # NOT NULL desde 20260828_0001 — ver a nota em Workflow.workspace_id.
    # Gravado no despacho e nunca alterado: e o tenant que de fato produziu esta
    # execucao, mesmo que o workflow seja movido depois.
    workspace_id = Column(String(36), nullable=False, index=True)
    schedule_id = Column(Integer, ForeignKey('schedules.id', ondelete='SET NULL'), nullable=True)

    status = Column(String, nullable=False, default='running', index=True)
    exit_code = Column(Integer, nullable=True)
    host = Column(String, nullable=True)
    # Nível da política em que o job foi ENTREGUE: "primary" | "fallback" |
    # "pool". Gravado junto com `host` (INSERT e failover) — é o que torna
    # "rodou no fallback/pool" observável por run, mesmo que a política do
    # workspace mude depois. Nulo em runs anteriores à coluna.
    dispatch_tier = Column(String(8), nullable=True)
    # Origem do disparo e quem disparou (docs/specs/historico-metricas.md §2):
    # "manual" | "retry" | "webhook" | "schedule". `triggered_by` é o id_hash
    # do usuário nas rotas autenticadas; nulo em webhook e agendamento. Runs
    # anteriores à coluna ficam nulos — a tela mostra "—".
    trigger_source = Column(String(16), nullable=True)
    triggered_by = Column(String(36), nullable=True)
    # Categoria do erro que fechou o run: a taxonomia do flow (user, validation,
    # timeout, resource, transient, internal) mais as do servidor (no_executor,
    # executor_lost, isolation, dispatch). É o que permite "por que falha" sem
    # LIKE em `error_message`.
    error_category = Column(String(16), nullable=True)

    start_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    node_stats = Column(JSON, nullable=True)

    # PERF: lazy='raise' evita N+1 acidental em listagens (antes: selectin carregava
    # Workflow+Schedule para CADA run → 101 queries para listar 50 runs).
    # Endpoints que precisam devem usar selectinload() explícito na query.
    workflow = relationship(
        'Workflow',
        back_populates='runs',
        primaryjoin='Workflow.id_hash==WorkflowRun.workflow_hash',
        lazy='raise',
    )
    schedule = relationship('Schedule', lazy='raise')
