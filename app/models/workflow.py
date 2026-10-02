# app/models/workflow.py
from sqlalchemy import (
    Column, Integer, String, JSON, ForeignKey, DateTime, Text, Boolean, Index, func, text,
)
from sqlalchemy.orm import relationship
from uuid import uuid4
from app.models.base import Base


class Workflow(Base):
    __tablename__ = 'workflows'
    __table_args__ = (
        Index('ix_workflow_workspace_active', 'workspace_id', 'flag_ative'),
        # PARCIAL: o nome so e unico entre os workflows VIVOS. O delete e soft
        # (soft_delete_by_hash mantem a linha e grava deleted_at), entao uma
        # restricao total deixava o nome de tudo que se apagava ocupado para
        # sempre — e de forma invisivel, ja que nenhuma listagem mostra
        # soft-deletados. Duplicar, criar e renomear batiam nesse muro.
        #
        # O nome do indice repete o da constraint anterior de proposito:
        # workflow_service e workflow_move_service reconhecem a colisao por
        # `"uq_workflow_name_workspace" in str(exc.orig)`.
        # `sqlite_where` junto do `postgresql_where`: os testes montam schema com
        # `metadata.create_all` sobre SQLite, e um dialeto que ignora o predicado
        # cria indice unico TOTAL — o oposto do que este indice significa. Sem os
        # dois, um teste da semantica parcial passaria em produção e falharia na
        # suite (ou pior, o contrario).
        Index(
            'uq_workflow_name_workspace', 'name', 'workspace_id',
            unique=True,
            postgresql_where=text('deleted_at IS NULL'),
            sqlite_where=text('deleted_at IS NULL'),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, default=lambda: str(uuid4()), nullable=False, index=True)
    flag_ative = Column(Boolean, default=True, nullable=False)

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String, nullable=True)
    priority = Column(Integer, default=0)
    # NOT NULL desde 20260828_0001: enquanto a coluna aceitava NULL, os filtros
    # de tenant carregavam um `OR workspace_id IS NULL` que tornava a linha
    # visivel a QUALQUER usuario autenticado.
    workspace_id = Column(String(36), nullable=False, index=True)
    group_id = Column(String(36), ForeignKey('workflow_groups.id_hash', ondelete='SET NULL'), nullable=True, index=True)
    params_schema = Column(JSON, nullable=True)
    notification_url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by_id = Column(String(36), nullable=True)
    updated_by_id = Column(String(36), nullable=True)

    # Proveniencia do fluxo, nao privilegio: "usuario" (o padrao) ou "assistente"
    # (criado pelo assistente da Home, escondido das listagens por padrao). Um
    # dia absorve "importado"/"template"/"duplicado"; por isso VARCHAR e nao
    # Boolean. NOT NULL com server_default: todo fluxo existente vira "usuario"
    # sem backfill.
    origem = Column(String(16), nullable=False, server_default=text("'usuario'"))

    definition = Column(JSON, nullable=False)
    pinned_outputs = Column(JSON, nullable=True)
    pin_metadata = Column(JSON, nullable=True)

    portal_access = Column(String(16), nullable=False, server_default="disabled")
    portal_shared_with = Column(JSON, nullable=True)
    deleted_at = Column(DateTime, nullable=True, default=None)

    group = relationship('WorkflowGroup', back_populates='workflows', foreign_keys=[group_id])
    schedules = relationship("Schedule", back_populates="workflow", cascade="all, delete-orphan")
    runs = relationship('WorkflowRun', back_populates='workflow', cascade='all, delete')
    versions = relationship('WorkflowVersion', back_populates='workflow', cascade='all, delete-orphan', order_by='WorkflowVersion.version_number')
