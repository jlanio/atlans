# schemas/credential.py
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime


def _normalize_tags(tags: Optional[List[str]]) -> Optional[List[str]]:
    """Cleans up and limits the tags: no empty ones, no duplicates, at most 10.

    Preserves the order of first appearance — deduplicating with a set would
    lose the order the user typed.
    """
    if tags is None:
        return None
    vistos: set[str] = set()
    out: List[str] = []
    for t in tags:
        t = (t or "").strip()
        if not t or t in vistos:
            continue
        vistos.add(t)
        out.append(t[:40])
        if len(out) >= 10:
            break
    return out


class _CredentialWritable(BaseModel):
    """Fields shared by create and edit (everything but `data`)."""
    name: str = Field(..., description="Nome visível da credencial")
    type: str = Field(..., description="Tipo da credencial (ex: postgresql, webhook_token, etc.)")
    description: Optional[str] = Field(default=None, max_length=200, description="Nota curta, não-secreta")
    tags: Optional[List[str]] = Field(default=None, description="Tags de organização")
    workspace_id: Optional[str] = Field(
        default=None,
        description="Se preenchido, compartilha a credencial com os membros do workspace",
    )

    @field_validator("tags")
    @classmethod
    def _tags(cls, v):
        return _normalize_tags(v)

    @field_validator("description")
    @classmethod
    def _desc(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v or None


class CredentialCreate(_CredentialWritable):
    data: Dict[str, str] = Field(..., description="Dados sensíveis a serem criptografados")


class CredentialUpdate(_CredentialWritable):
    """Edit. `data` is OPTIONAL — absent/empty means 'keep the current secrets'
    (write-only partial rotation). See credential_service.update_credential.
    """
    data: Optional[Dict[str, str]] = Field(
        default=None,
        description="Segredos a gravar. Omita para manter os existentes.",
    )


class CredentialTestRequest(BaseModel):
    type: str = Field(..., description="Tipo da credencial a ser testada")
    data: Dict[str, str] = Field(..., description="Campos da credencial (não criptografados)")


class CredentialOut(BaseModel):
    id: UUID
    name: str
    type: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    # owner_id (the creator's id_hash) lets the UI distinguish "my credential"
    # from "shared with me" and hide Edit/Delete from non-owners — editing and
    # deleting remain owner-only in the backend anyway.
    owner_id: Optional[str] = None
    workspace_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None
    # Filled in by the model's @property (derived from data['expires_at']).
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # substitui orm_mode = True


class CredentialOutWithData(CredentialOut):
    """Includes the decrypted data — used by the edit endpoint."""
    data: Dict[str, str] = {}
