# app/models/api_token.py
"""
Token pessoal de acesso (PAT) de um usuário — a identidade de um agente.

Ciclo de vida:
  1. O usuário cria o token na tela «Tokens de acesso» (POST /auth/tokens):
     nome, escopos, workspaces alcançados e validade. O segredo (`atl_pat_…`)
     aparece UMA vez na resposta; aqui fica só o SHA-256 (`token_hash`) e um
     prefixo curto (`token_prefix`) para ele reconhecer o token na lista.
  2. Um agente manda `Authorization: Bearer atl_pat_…`; o servidor faz o hash,
     acha a linha por `token_hash`, exige `revoked_at IS NULL`, `expires_at`
     no futuro e usuário ativo (api_token_service.resolver).
  3. `last_used_at` é carimbado best-effort, com throttle de 60 s no Redis.
  4. Revogação é marcação (`revoked_at` + `revoked_reason`), nunca DELETE:
     pelo usuário ("user"), por reset de senha ("password_reset") ou em
     cascata quando a conta é suspensa/excluída ("user_suspended"/"user_deleted").
     Reativar a conta NÃO desfaz a revogação.

`workspace_ids` NULL significa "todos os workspaces do usuário, inclusive os
que ele entrar depois" — escolha explícita na tela. `scopes` é a lista de
escopos (ver app/core/authorization/pat.py); o efetivo é escopo ∩ papel do
usuário no workspace, aplicado por quem consome o token.
"""
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, func

from app.models.base import Base


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid4()))
    # User.id_hash do dono. CASCADE só no hard delete do usuário (soft delete
    # revoga em cascata pelo service).
    user_id = Column(String(36), ForeignKey("users.id_hash", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(80), nullable=False)
    # Os 12 primeiros caracteres do segredo ("atl_pat_" + 4) — para exibir.
    token_prefix = Column(String(16), nullable=False)
    # SHA-256 hex do segredo. Único: é a chave do lookup de autenticação.
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    scopes = Column(JSON, nullable=False)
    workspace_ids = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    # "user" | "password_reset" | "user_suspended" | "user_deleted"
    revoked_reason = Column(String(32), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
