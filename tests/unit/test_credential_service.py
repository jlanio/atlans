# tests/unit/test_credential_service.py
"""Semantics of credential create/update/list.

Covers what previously had no test at all and started to hold in this round:
- validation of required fields on WRITE (before, create/update never
  validated — you could save postgresql without a password);
- write-only rotation: a partial `data` MERGES instead of wiping the other
  secrets, and an absent `data` keeps everything;
- metadata with PATCH semantics (omitting preserves, null clears);
- listing scope (owner ∪ shared);
- the expires_at property derived from data['expires_at'].
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.crud.credential_crud import CredentialCRUD
from app.models.credential import Credential
from app.schemas.credential import CredentialCreate, CredentialOut, CredentialUpdate
from app.services import credential_service as svc
from app.core.exceptions import CredentialValidationError


def _db():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


# Simulated encryption: reversible and inspectable (ENC(x) <-> x). The model
# imports encrypt_string into its own namespace; the service imports
# decrypt_credential_data into its own.
def _enc(v):
    return "ENC(" + v + ")"


def _dec(d):
    return {k: (v[4:-1] if isinstance(v, str) and v.startswith("ENC(") else v) for k, v in d.items()}


def _patch_cripto():
    return [
        patch("app.models.credential.encrypt_string", side_effect=_enc),
        patch("app.services.credential_service.decrypt_credential_data", side_effect=_dec),
    ]


def _with_crypto(fn):
    async def wrapper(*a, **k):
        from contextlib import ExitStack
        with ExitStack() as stack:
            for p in _patch_cripto():
                stack.enter_context(p)
            return await fn(*a, **k)
    return wrapper


def _patch_get(cred):
    async def _get(self, cid):
        return cred
    return patch.object(CredentialCRUD, "get", _get)


# ── create: validation ───────────────────────────────────────────────────────

async def test_create_rejects_missing_required_field():
    with _patch_cripto()[0], _patch_cripto()[1]:
        with pytest.raises(CredentialValidationError, match="Senha"):
            await svc.create_credential(
                CredentialCreate(name="c", type="postgresql",
                                 data={"host": "h", "database": "d", "user": "u"}),
                _db(),
            )


async def test_create_free_type_does_not_validate():
    """A type outside the catalog stays free-form — it is the props editor's fallback."""
    with _patch_cripto()[0], _patch_cripto()[1]:
        cred = await svc.create_credential(
            CredentialCreate(name="c", type="tipo_custom", data={"qualquer": "coisa"}),
            _db(), owner_id="o",
        )
    assert cred.type == "tipo_custom"
    assert cred.data["qualquer"] == "ENC(coisa)"


async def test_create_stores_metadata_and_owner():
    with _patch_cripto()[0], _patch_cripto()[1]:
        cred = await svc.create_credential(
            CredentialCreate(
                name="c", type="s3",
                data={"access_key_id": "a", "secret_access_key": "s", "region": "r"},
                description="nota", tags=["x", "x", "y"], workspace_id="ws-1",
            ),
            _db(), owner_id="owner-1",
        )
    assert cred.owner_id == "owner-1"
    assert cred.workspace_id == "ws-1"
    assert cred.description == "nota"
    assert cred.tags == ["x", "y"]           # schema dedupe


# ── update: write-only rotation ───────────────────────────────────────────────

def _cred_pg():
    c = Credential(name="old", type="postgresql", owner_id="owner-1")
    c.data = {
        "host": "ENC(h)", "port": "5432", "database": "ENC(db)",
        "user": "ENC(u)", "password": "ENC(oldpw)", "connectionString": "ENC(dsn-antiga)",  # pragma: allowlist secret
    }
    return c


async def test_update_partial_merge_preserves_and_rebuilds_dsn():
    """Sending only the password changes only the password; host/user stay, and the DSN is recomputed."""
    cred = _cred_pg()
    with _patch_get(cred), _patch_cripto()[0], _patch_cripto()[1]:
        out = await svc.update_credential(
            uuid4(), CredentialUpdate(name="n", type="postgresql", data={"password": "newpw"}),  # pragma: allowlist secret
            _db(), owner_id="owner-1",
        )
    dec = _dec(out.data)
    assert dec["password"] == "newpw"  # pragma: allowlist secret
    assert dec["host"] == "h" and dec["user"] == "u" and dec["database"] == "db"
    assert dec["connectionString"] == "postgresql://u:newpw@h:5432/db"  # pragma: allowlist secret


async def test_update_without_data_keeps_secrets():
    cred = Credential(name="old", type="s3", owner_id="owner-1")
    cred.data = {"access_key_id": "ENC(a)", "secret_access_key": "ENC(s)", "region": "ENC(r)"}
    snapshot = dict(cred.data)
    with _patch_get(cred), \
         patch("app.models.credential.encrypt_string", side_effect=lambda v: "NAO_DEVIA_RODAR"), \
         patch("app.services.credential_service.decrypt_credential_data", side_effect=_dec):
        out = await svc.update_credential(
            uuid4(), CredentialUpdate(name="renomeada", type="s3"),
            _db(), owner_id="owner-1",
        )
    assert out.data == snapshot
    assert out.name == "renomeada"


async def test_update_empty_data_also_keeps():
    """`data={}` (empty dict) is treated as 'no secret change', not a wipe."""
    cred = Credential(name="old", type="s3", owner_id="owner-1")
    cred.data = {"access_key_id": "ENC(a)", "secret_access_key": "ENC(s)", "region": "ENC(r)"}
    snapshot = dict(cred.data)
    with _patch_get(cred), \
         patch("app.models.credential.encrypt_string", side_effect=lambda v: "NAO_DEVIA_RODAR"), \
         patch("app.services.credential_service.decrypt_credential_data", side_effect=_dec):
        out = await svc.update_credential(
            uuid4(), CredentialUpdate(name="n", type="s3", data={}),
            _db(), owner_id="owner-1",
        )
    assert out.data == snapshot


async def test_update_free_type_preserves_connectionstring_key():
    """A free-form type can have a literal 'connectionString' key — the merge does
    not discard it (only database types treat it as derived)."""
    cred = Credential(name="c", type="tipo_custom", owner_id="owner-1")
    cred.data = {"connectionString": "ENC(algo-do-usuario)", "outro": "ENC(v)"}
    with _patch_get(cred), _patch_cripto()[0], _patch_cripto()[1]:
        out = await svc.update_credential(
            uuid4(), CredentialUpdate(name="c", type="tipo_custom", data={"outro": "novo"}),
            _db(), owner_id="owner-1",
        )
    dec = _dec(out.data)
    assert dec["connectionString"] == "algo-do-usuario"   # preservada
    assert dec["outro"] == "novo"


async def test_update_invalid_merge_is_rejected():
    """If the merge leaves a required field empty, the update is rejected (422)."""
    cred = _cred_pg()
    with _patch_get(cred), _patch_cripto()[0], _patch_cripto()[1]:
        with pytest.raises(CredentialValidationError, match="Senha"):
            await svc.update_credential(
                uuid4(), CredentialUpdate(name="n", type="postgresql", data={"password": ""}),
                _db(), owner_id="owner-1",
            )


async def test_update_that_changes_the_type_keeps_only_the_new_fields():
    """From postgresql to authkey: host/user/password and the old DSN do not stay
    encrypted in the blob of a credential of another type (the resolver would
    have had to learn to ignore them)."""
    cred = _cred_pg()
    with _patch_get(cred), _patch_cripto()[0], _patch_cripto()[1]:
        out = await svc.update_credential(
            uuid4(), CredentialUpdate(name="n", type="geoserver_authkey", data={"token": "c0ffee-SEGREDO-42"}),
            _db(), owner_id="owner-1",
        )
    assert _dec(out.data) == {"token": "c0ffee-SEGREDO-42"}


async def test_update_that_stops_being_database_does_not_carry_the_dsn():
    """postgresql → free-form type: the derived DSN (with the password) does not
    stay in the blob, otherwise a database node would still receive it; the
    other fields stay (a free-form type has no schema to say which ones count)."""
    cred = _cred_pg()
    with _patch_get(cred), _patch_cripto()[0], _patch_cripto()[1]:
        out = await svc.update_credential(
            uuid4(), CredentialUpdate(name="n", type="tipo_custom", data={"outro": "novo"}), _db(), owner_id="owner-1",
        )
    dados = _dec(out.data)
    assert "connectionString" not in dados and dados["outro"] == "novo" and dados["host"] == "h"


async def test_stored_non_string_value_does_not_break_validation():
    # The type change validates the `data` already stored; a legacy numeric port
    # must not turn into a 500.
    assert svc.validation_error("postgresql", {"host": "h", "port": 5432, "database": "d", "user": "u", "password": "p"}) is None
    assert svc.validation_error("postgresql", {"host": 0, "database": "d", "user": "u", "password": "p"}) == "Campos obrigatórios ausentes: Host"


async def test_update_that_changes_the_type_without_data_requires_the_new_fields():
    """Changing only the type, without sending its fields, would store a
    credential that no node can use."""
    cred = _cred_pg()
    with _patch_get(cred), _patch_cripto()[0], _patch_cripto()[1]:
        with pytest.raises(CredentialValidationError, match="Chave"):
            await svc.update_credential(
                uuid4(), CredentialUpdate(name="n", type="geoserver_authkey"), _db(), owner_id="owner-1",
            )


# ── the WFS node's rules apply on save and on Test ───────────────────────────

async def test_create_rejects_what_the_wfs_node_would_reject():
    with _patch_cripto()[0], _patch_cripto()[1]:
        with pytest.raises(CredentialValidationError, match="parâmetro do próprio WFS"):
            await svc.create_credential(
                CredentialCreate(name="c", type="geoserver_authkey", data={"token": "c0ffee-SEGREDO-42", "parameter": "bbox"}),
                _db(),
            )
        with pytest.raises(CredentialValidationError, match="menos de 6 caracteres"):
            await svc.create_credential(
                CredentialCreate(name="c", type="wfs", data={"username": "u", "password": "geo"}), _db(),  # pragma: allowlist secret
            )


def test_validation_error_is_the_same_rule_as_test():
    assert svc.validation_error("geoserver_authkey", {"token": "c0ffee-SEGREDO-42"}) is None
    assert svc.validation_error("geoserver_authkey", {"token": ""}) == "Campos obrigatórios ausentes: Chave (authkey)"
    assert "cabeçalho" in svc.validation_error(
        "geoserver_authkey", {"token": "c0ffee-SEGREDO-42", "parameter": "Host", "location": "header"},
    )
    assert svc.validation_error("tipo_custom", {}) is None


# ── update: metadados PATCH-like ──────────────────────────────────────────────

async def test_update_omitting_metadata_preserves():
    cred = Credential(name="old", type="s3", owner_id="o", description="mantem", workspace_id="ws")
    cred.tags = ["a"]
    cred.data = {"access_key_id": "ENC(a)", "secret_access_key": "ENC(s)", "region": "ENC(r)"}
    with _patch_get(cred), \
         patch("app.models.credential.encrypt_string", side_effect=_enc), \
         patch("app.services.credential_service.decrypt_credential_data", side_effect=_dec):
        out = await svc.update_credential(
            uuid4(), CredentialUpdate(name="n", type="s3"), _db(), owner_id="o",
        )
    assert out.description == "mantem" and out.tags == ["a"] and out.workspace_id == "ws"


async def test_update_explicit_null_clears():
    cred = Credential(name="old", type="s3", owner_id="o", description="some", workspace_id="ws")
    cred.tags = ["a"]
    cred.data = {"access_key_id": "ENC(a)", "secret_access_key": "ENC(s)", "region": "ENC(r)"}
    with _patch_get(cred), \
         patch("app.models.credential.encrypt_string", side_effect=_enc), \
         patch("app.services.credential_service.decrypt_credential_data", side_effect=_dec):
        out = await svc.update_credential(
            uuid4(),
            CredentialUpdate(name="n", type="s3", description=None, workspace_id=None),
            _db(), owner_id="o",
        )
    assert out.description is None and out.workspace_id is None
    assert out.tags == ["a"]   # tags was omitted → preserved


# ── list: escopo ──────────────────────────────────────────────────────────────

async def test_list_merges_owned_and_shared():
    db = MagicMock()
    res = MagicMock()
    res.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=res)
    await svc.list_credential_metadata(db, owner_id="me", type="s3", workspace_ids=["ws1", "ws2"])
    stmt = str(db.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True}))
    where = stmt.split("WHERE", 1)[1]
    assert "owner_id" in where and "me" in where
    assert "workspace_id" in where and "ws1" in where
    assert " OR " in where


# ── model.expires_at property ─────────────────────────────────────────────────

def test_expires_at_property_derives_from_data():
    c = Credential(name="c", type="webhook_token", data={"expires_at": "2027-05-01T00:00:00Z"})
    assert c.expires_at is not None and c.expires_at.year == 2027


def test_expires_at_property_missing_or_invalid():
    assert Credential(name="c", type="s3", data={"x": "y"}).expires_at is None
    assert Credential(name="c", type="s3", data={"expires_at": "lixo"}).expires_at is None
    assert Credential(name="c", type="s3", data=None).expires_at is None


def test_credential_out_fills_expires_at_via_property():
    c = Credential(name="c", type="webhook_token", data={"expires_at": "2027-05-01T00:00:00Z"})
    c.id = uuid4()
    c.created_at = c.updated_at = datetime.utcnow()
    out = CredentialOut.model_validate(c)
    assert out.expires_at is not None and out.expires_at.year == 2027


def test_encrypt_and_store_always_encrypts_value_with_gaaaa_prefix():
    """Audit SEG-19: a value the client sends starting with 'gAAAA' (someone
    else's ciphertext) must NOT be stored in the clear — otherwise GET /data
    would decrypt it with the platform key (an oracle). Now it is always
    encrypted, and decrypting returns the 'gAAAA…' string itself, never a
    secret."""
    from app.models.credential import Credential
    from app.core.utils.encryption import decrypt_credential_data

    fake_ciphertext = "gAAAAA-conteudo-cifrado-de-outra-pessoa"
    cred = Credential(type="http_bearer", name="x")
    cred.encrypt_and_store({"token": fake_ciphertext})
    # It was encrypted (did not stay the same as what came in).
    assert cred.data["token"] != fake_ciphertext
    assert cred.data["token"].startswith("gAAAA")
    # And decrypting returns the original string, not someone else's secret.
    assert decrypt_credential_data(cred.data)["token"] == fake_ciphertext
