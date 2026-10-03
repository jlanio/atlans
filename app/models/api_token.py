# app/models/api_token.py
"""
A user's personal access token (PAT) — an agent's identity.

Lifecycle:
  1. The user creates the token on the "Tokens de acesso" (access tokens)
     screen (POST /auth/tokens): name, scopes, workspaces reached and
     validity. The secret (`atl_pat_…`) appears ONCE in the response; here only
     the SHA-256 (`token_hash`) is kept, plus a short prefix (`token_prefix`)
     for the user to recognize the token in the list.
  2. An agent sends `Authorization: Bearer atl_pat_…`; the server hashes it,
     finds the row by `token_hash`, requires `revoked_at IS NULL`, `expires_at`
     in the future and an active user (api_token_service.resolver).
  3. `last_used_at` is stamped best-effort, throttled to 60 s in Redis.
  4. Revocation is a marker (`revoked_at` + `revoked_reason`), never DELETE:
     by the user ("user"), by a password reset ("password_reset") or in
     cascade when the account is suspended/deleted ("user_suspended"/"user_deleted").
     Reactivating the account does NOT undo the revocation.

`workspace_ids` NULL means "all the user's workspaces, including the ones they
join later" — an explicit choice on the screen. `scopes` is the list of scopes
(see app/core/authorization/pat.py); the effective one is scope ∩ the user's
role in the workspace, enforced by whoever consumes the token.
"""
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, func

from app.models.base import Base


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid4()))
    # The owner's User.id_hash. CASCADE only on the user's hard delete (soft
    # delete revokes in cascade through the service).
    user_id = Column(String(36), ForeignKey("users.id_hash", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(80), nullable=False)
    # The first 12 characters of the secret ("atl_pat_" + 4) — for display.
    token_prefix = Column(String(16), nullable=False)
    # Hex SHA-256 of the secret. Unique: it is the authentication lookup key.
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    scopes = Column(JSON, nullable=False)
    workspace_ids = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    # "user" | "password_reset" | "user_suspended" | "user_deleted"
    revoked_reason = Column(String(32), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
