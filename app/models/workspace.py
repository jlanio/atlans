# app/models/workspace.py
from sqlalchemy import Boolean, Column, Integer, JSON, String, DateTime, func
from uuid import uuid4
from app.models.base import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, default=lambda: str(uuid4()), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    # index: get_user_workspace_ids filtra por owner_id em quase toda request
    # autenticada; sem índice era seq scan por requisição.
    owner_id = Column(String(36), nullable=True, index=True)   # User.id_hash do criador
    # Executor vinculado ao workspace — todos os workflows herdam este executor.
    # Nome SQL "target_executor_id" (renomeada em 20260716_0001); atributo
    # Python mantido como target_executor_id ate R2.3. index: roteamento
    # reverso (get_agent_workspace_ids) filtra por esta coluna.
    target_executor_id = Column("target_executor_id", String(36), nullable=True, index=True)
    # Política de execução (docs/specs/executor-isolation-routing.md, §4.2).
    # Os NÍVEIS de executores dedicados vivem em `workspace_executors`; aqui
    # ficam só o terminal e o piso:
    #   fallback_terminal: o que fazer quando a cadeia de níveis se esgota —
    #     "fail" (Isolado: nunca pool) ou "pool" (Dedicado com fallback).
    #     Só é lido quando há nível 1; default seguro = "fail" (Q8).
    #   isolation_floor: "none" | "no_pool". Só o admin da plataforma escreve;
    #     "no_pool" força o terminal efetivo a "fail" — inclusive no dispatch,
    #     diga o que disser fallback_terminal (defesa em profundidade).
    fallback_terminal = Column(String(8), nullable=False, server_default="fail", default="fail")
    isolation_floor = Column(String(8), nullable=False, server_default="none", default="none")
    # Workspace padrão do usuário — não pode ser excluído
    is_default = Column(Boolean, nullable=False, server_default="false", default=False)
    # Allowlist de hostnames (lista de strings) aceitos como notification_url
    # de workflows deste workspace. None ou [] significa que vale apenas o
    # SSRF check default (sem politica adicional). Padroes aceitos: "host.tld"
    # (match exato) e "*.host.tld" (subdominios). Validado em
    # run_result_consumer._fire_notification_if_configured.
    notification_url_allowlist = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    # Soft delete — toda leitura de workspace filtra `deleted_at IS NULL`. O
    # timestamp e compartilhado com os workflows desativados em cascata: e ele
    # que identifica, no restore, quais workflows cairam por causa do delete do
    # workspace e quais ja estavam deletados antes.
    deleted_at = Column(DateTime, nullable=True, default=None)
