# services/credential_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.exceptions import (
    CredentialNotFoundError,
    CredentialAccessDeniedError,
    CredentialValidationError,
)
from app.crud.credential_crud import CredentialCRUD
from app.models.credential import Credential
from app.schemas.credential import CredentialCreate, CredentialUpdate
from app.core.credentials.connection_builder import build_connection_data, validate_required_fields
from app.core.credentials.schemas import CREDENTIAL_TYPE_SCHEMAS
from app.core.utils.encryption import decrypt_credential_data
from flow.utils.credencial_wfs import autenticacao_wfs

# The types the WFS node reads: saving and "Testar" (Test) apply ITS rules.
_TIPOS_DO_WFS = ("geoserver_authkey", "wfs")
# The types whose `connectionString` is DERIVED from the fields (see connection_builder).
_TIPOS_DE_BANCO = ("postgresql", "mysql")


def erro_de_validacao(cred_type: str, data: dict) -> str | None:
    """Why the credential cannot be saved — or None.

    Required fields of a KNOWN type and, for the WFS ones, what the node would
    reject at execution (key too short to be protected in the logs, parameter
    name that belongs to WFS itself, reserved header...): the Credentials
    screen warns on save and on Test, instead of the workflow failing on its
    first run. Types outside the catalog remain free-form (the props editor is
    precisely their fallback).
    """
    erro = validate_required_fields(cred_type, data)
    if erro:
        return erro
    if cred_type in _TIPOS_DO_WFS:
        try:
            autenticacao_wfs(None, {**data, "type": cred_type})
        except ValueError as exc:
            return str(exc)
    return None


def _validate_or_raise(cred_type: str, data: dict) -> None:
    """Rejects the save if required fields of a KNOWN type are missing.

    Before, create/update NEVER validated: you could save a postgresql one with
    no password, and build_connection_data filled the gaps with defaults,
    producing `postgresql://:@localhost:5432/` — a plausible credential that only
    failed when the workflow executed.
    """
    erro = erro_de_validacao(cred_type, data)
    if erro:
        raise CredentialValidationError(erro)


async def create_credential(data: CredentialCreate, db: AsyncSession, owner_id: str | None = None) -> Credential:
    _validate_or_raise(data.type, data.data)
    # Enriches the data with connectionString and other fields derived from the type
    enriched = build_connection_data(data.type, data.data)
    cred = Credential(
        name=data.name,
        type=data.type,
        owner_id=owner_id,
        workspace_id=data.workspace_id,
        description=data.description,
        tags=data.tags,
    )
    cred.encrypt_and_store(enriched)
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return cred


async def get_credential_metadata(db: AsyncSession, cred_id: UUID, owner_id: str | None = None) -> Credential:
    cred = await CredentialCRUD(db).get(cred_id)
    if not cred:
        raise CredentialNotFoundError("Credencial não encontrada")
    # Checks ownership, fail-closed: a credential with NO owner is inaccessible to all.
    #
    # Before, the condition required a truthy `cred.owner_id`, so a credential with
    # a NULL owner_id short-circuited the check and was read, edited and deleted by
    # any authenticated user — including from another tenant, given just the UUID
    # (which travels in the clear inside Workflow.definition, in properties.credential_id).
    # And orphans do exist: credential_loader already logs "Credencial %s não tem dono
    # (owner_id nulo)". Since this is the only authorization point for GET/PUT/DELETE
    # /credentials/{cred_id} and for GET /credentials/{cred_id}/data — which returns
    # the decrypted secret —, denying is the correct default.
    #
    # SCOPE of this check: ownership (owner-only). Sharing by workspace only
    # widens READ access to metadata (the listing) and use in execution;
    # editing, deleting and reading the SECRET (/data) remain restricted to the
    # owner.
    if owner_id and cred.owner_id != owner_id:
        raise CredentialAccessDeniedError("Acesso negado a esta credencial.")
    return cred


async def delete_credential(db: AsyncSession, cred_id: UUID, owner_id: str | None = None):
    cred = await get_credential_metadata(db, cred_id, owner_id=owner_id)
    await db.delete(cred)
    await db.commit()


async def update_credential(cred_id: UUID, update_data: CredentialUpdate, db: AsyncSession, owner_id: str | None = None) -> Credential:
    cred = await get_credential_metadata(db, cred_id, owner_id=owner_id)

    # PATCH-like semantics for the metadata: only touches what the client SENT.
    # `model_fields_set` distinguishes "field omitted" from "field sent as null".
    # Without it, a PUT without `description` (the legacy frontend sends only
    # name/type/data) would wipe the description/tags/workspace_id already saved.
    # With it, omitting preserves and sending null clears — on purpose.
    enviados = update_data.model_fields_set
    tipo_anterior = cred.type
    cred.name = update_data.name
    cred.type = update_data.type
    if "description" in enviados:
        cred.description = update_data.description
    if "tags" in enviados:
        cred.tags = update_data.tags
    if "workspace_id" in enviados:
        cred.workspace_id = update_data.workspace_id

    # Write-only rotation/editing of secrets.
    #
    # `data` absent/empty ⇒ keeps the current secrets intact (the common case of
    # editing only the name or the sharing). `data` present ⇒ MERGE over the
    # existing decrypted secrets: the client sends only the fields that changed,
    # and whatever it did not send is preserved.
    #
    # This removes the old destructive path: encrypt_and_store does
    # `self.data = {...}` (replaces the whole blob), so a PARTIAL `data` used to
    # wipe all the other secrets. Now partial is safe and becomes the rotation
    # mechanism — changing only the password sends only the password.
    #
    # When the TYPE changes, `data` is rewritten even with no `data` in the
    # request: the old type's fields (the DSN from when it was a database one,
    # the `token` from when it was Bearer) do not stay encrypted in the blob of a
    # credential of another type — and the new type must have its required
    # fields, otherwise the change would save a credential no node can use.
    mudou_de_tipo = update_data.type != tipo_anterior
    if update_data.data or mudou_de_tipo:
        atuais = decrypt_credential_data(cred.data or {})
        # For database types the connectionString is DERIVED (recomputed from
        # host/user/... by build_connection_data further on), so the old one does
        # not stay — not even in a credential that STOPPED being a database one,
        # where the DSN with the old password would keep being injected into a
        # database node. For a free-form type that was always free-form,
        # "connectionString" may be a legitimate user field: then it is NOT touched.
        if update_data.type in _TIPOS_DE_BANCO or tipo_anterior in _TIPOS_DE_BANCO:
            atuais.pop("connectionString", None)
        mesclado = {**atuais, **(update_data.data or {})}
        esquema = CREDENTIAL_TYPE_SCHEMAS.get(update_data.type)
        if mudou_de_tipo and esquema is not None:
            permitidas = {f.key for f in esquema.fields} | {"expires_at"}
            mesclado = {k: v for k, v in mesclado.items() if k in permitidas}
        _validate_or_raise(update_data.type, mesclado)
        enriched = build_connection_data(update_data.type, mesclado)
        cred.encrypt_and_store(enriched)

    await db.commit()
    await db.refresh(cred)
    return cred


async def list_credential_metadata(
    db: AsyncSession,
    owner_id: str | None = None,
    type: str | None = None,
    workspace_ids: list[str] | None = None,
) -> list[Credential]:
    return await CredentialCRUD(db).list(owner_id=owner_id, type=type, workspace_ids=workspace_ids)
