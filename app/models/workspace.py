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
    # index: get_user_workspace_ids filters by owner_id on almost every
    # authenticated request; without an index it was a seq scan per request.
    owner_id = Column(String(36), nullable=True, index=True)   # Creator's User.id_hash
    # Executor bound to the workspace — all workflows inherit this executor.
    # SQL name "target_executor_id" (renamed in 20260716_0001); Python
    # attribute kept as target_executor_id until R2.3. index: reverse
    # routing (get_agent_workspace_ids) filters by this column.
    target_executor_id = Column("target_executor_id", String(36), nullable=True, index=True)
    # Execution policy (docs/specs/executor-isolation-routing.md, §4.2).
    # The TIERS of dedicated executors live in `workspace_executors`; only the
    # terminal and the floor are kept here:
    #   fallback_terminal: what to do when the chain of tiers runs out —
    #     "fail" (Isolated: never pool) or "pool" (Dedicated with fallback).
    #     Only read when there is a tier 1; safe default = "fail" (Q8).
    #   isolation_floor: "none" | "no_pool". Only the platform admin writes it;
    #     "no_pool" forces the effective terminal to "fail" — dispatch included,
    #     whatever fallback_terminal says (defense in depth).
    fallback_terminal = Column(String(8), nullable=False, server_default="fail", default="fail")
    isolation_floor = Column(String(8), nullable=False, server_default="none", default="none")
    # The user's default workspace — cannot be deleted
    is_default = Column(Boolean, nullable=False, server_default="false", default=False)
    # Allowlist of hostnames (list of strings) accepted as notification_url
    # for this workspace's workflows. None or [] means only the default SSRF
    # check applies (no additional policy). Accepted patterns: "host.tld"
    # (exact match) and "*.host.tld" (subdomains). Validated in
    # run_result_consumer._fire_notification_if_configured.
    notification_url_allowlist = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    # Soft delete — every workspace read filters `deleted_at IS NULL`. The
    # timestamp is shared with the workflows deactivated in cascade: it is what
    # identifies, on restore, which workflows went down because of the
    # workspace's deletion and which were already deleted before.
    deleted_at = Column(DateTime, nullable=True, default=None)
