# app/schemas/api_token.py
"""
Personal access token (PAT) schemas.

`ApiTokenCreated` is the only place where the secret appears — in the creation
response, once. After that the API only returns `ApiTokenOut` (prefix + metadata).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.authorization.pat import (
    ESCOPOS,
    VALIDADE_MAX_DIAS,
    VALIDADE_PADRAO_DIAS,
    escopos_invalidos,
    status_de,
)


class ApiTokenCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=80, description="Nome para reconhecer o token na lista")
    scopes: List[str] = Field(..., min_length=1, description=f"Escopos permitidos: {', '.join(ESCOPOS)}")
    workspace_ids: Optional[List[str]] = Field(
        default=None,
        description="Workspaces que o token alcança. null = todos os workspaces do usuário, inclusive os futuros",
    )
    expires_in_days: int = Field(
        default=VALIDADE_PADRAO_DIAS, ge=1, le=VALIDADE_MAX_DIAS,
        description=f"Validade em dias (1 a {VALIDADE_MAX_DIAS})",
    )

    @field_validator("name")
    @classmethod
    def _nome(cls, v: str) -> str:
        v = v.strip()
        if not v:
            # Same sentence as the service (which revalidates): the screen shows just one.
            raise ValueError("O nome precisa ter entre 1 e 80 caracteres.")
        return v

    @field_validator("scopes")
    @classmethod
    def _escopos(cls, v: List[str]) -> List[str]:
        unicos = list(dict.fromkeys(s.strip() for s in v if s and s.strip()))
        if not unicos:
            raise ValueError("Informe ao menos um escopo.")
        invalidos = escopos_invalidos(unicos)
        if invalidos:
            raise ValueError(f"Escopo desconhecido: {', '.join(invalidos)}.")
        return unicos

    @field_validator("workspace_ids")
    @classmethod
    def _workspaces(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        unicos = list(dict.fromkeys(w.strip() for w in v if w and w.strip()))
        if not unicos:
            raise ValueError("Informe ao menos um workspace, ou deixe em branco para todos.")
        return unicos


class ApiTokenOut(BaseModel):
    """Token metadata — never the secret."""
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    token_prefix: str
    scopes: List[str]
    workspace_ids: Optional[List[str]]
    expires_at: datetime
    last_used_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime
    # "active" | "expired" | "revoked" — computed at response time
    status: str

    @classmethod
    def de_modelo(cls, token, agora: datetime) -> "ApiTokenOut":
        return cls(
            id=token.id_hash,
            name=token.name,
            token_prefix=token.token_prefix,
            scopes=list(token.scopes or []),
            workspace_ids=list(token.workspace_ids) if token.workspace_ids is not None else None,
            expires_at=token.expires_at,
            last_used_at=token.last_used_at,
            revoked_at=token.revoked_at,
            created_at=token.created_at,
            status=status_de(token.revoked_at, token.expires_at, agora),
        )


class ApiTokenCreated(ApiTokenOut):
    """Creation response — the secret appears ONLY ONCE, here."""

    token: str

    @classmethod
    def com_segredo(cls, token, segredo: str, agora: datetime) -> "ApiTokenCreated":
        base = ApiTokenOut.de_modelo(token, agora)
        return cls(**base.model_dump(), token=segredo)
