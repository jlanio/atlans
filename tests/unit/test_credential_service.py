# tests/unit/test_credential_service.py
"""Semântica de create/update/list de credenciais.

Cobre o que antes não tinha teste nenhum e passou a valer nesta rodada:
- validação de campos obrigatórios na ESCRITA (antes create/update nunca
  validavam — dava para salvar postgresql sem senha);
- rotação write-only: `data` parcial faz MERGE em vez de apagar os outros
  segredos, e `data` ausente mantém tudo;
- metadados com semântica PATCH (omitir preserva, null limpa);
- escopo de listagem (dono ∪ compartilhadas);
- a property expires_at derivada de data['expires_at'].
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


# Encriptação simulada: reversível e inspecionável (ENC(x) <-> x). O modelo
# importa encrypt_string no seu próprio namespace; o service importa
# decrypt_credential_data no dele.
def _enc(v):
    return "ENC(" + v + ")"


def _dec(d):
    return {k: (v[4:-1] if isinstance(v, str) and v.startswith("ENC(") else v) for k, v in d.items()}


def _patch_cripto():
    return [
        patch("app.models.credential.encrypt_string", side_effect=_enc),
        patch("app.services.credential_service.decrypt_credential_data", side_effect=_dec),
    ]


def _com_cripto(fn):
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


# ── create: validação ────────────────────────────────────────────────────────

async def test_create_recusa_campo_obrigatorio_ausente():
    with _patch_cripto()[0], _patch_cripto()[1]:
        with pytest.raises(CredentialValidationError, match="Senha"):
            await svc.create_credential(
                CredentialCreate(name="c", type="postgresql",
                                 data={"host": "h", "database": "d", "user": "u"}),
                _db(),
            )


async def test_create_tipo_livre_nao_valida():
    """Tipo fora do catálogo segue livre — é o fallback do editor de props."""
    with _patch_cripto()[0], _patch_cripto()[1]:
        cred = await svc.create_credential(
            CredentialCreate(name="c", type="tipo_custom", data={"qualquer": "coisa"}),
            _db(), owner_id="o",
        )
    assert cred.type == "tipo_custom"
    assert cred.data["qualquer"] == "ENC(coisa)"


async def test_create_grava_metadados_e_dono():
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
    assert cred.tags == ["x", "y"]           # dedupe da schema


# ── update: rotação write-only ────────────────────────────────────────────────

def _cred_pg():
    c = Credential(name="old", type="postgresql", owner_id="owner-1")
    c.data = {
        "host": "ENC(h)", "port": "5432", "database": "ENC(db)",
        "user": "ENC(u)", "password": "ENC(oldpw)", "connectionString": "ENC(dsn-antiga)",  # pragma: allowlist secret
    }
    return c


async def test_update_merge_parcial_preserva_e_reconstroi_dsn():
    """Enviar só a senha muda só a senha; host/user ficam, e a DSN é recomputada."""
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


async def test_update_sem_data_mantem_segredos():
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


async def test_update_data_vazio_tambem_mantem():
    """`data={}` (dict vazio) é tratado como 'sem mudança de segredo', não wipe."""
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


async def test_update_tipo_livre_preserva_chave_connectionstring():
    """Tipo livre pode ter uma chave literal 'connectionString' — o merge não a
    descarta (só tipos de banco a tratam como derivada)."""
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


async def test_update_merge_invalido_e_recusado():
    """Se o merge deixar um obrigatório vazio, o update é recusado (422)."""
    cred = _cred_pg()
    with _patch_get(cred), _patch_cripto()[0], _patch_cripto()[1]:
        with pytest.raises(CredentialValidationError, match="Senha"):
            await svc.update_credential(
                uuid4(), CredentialUpdate(name="n", type="postgresql", data={"password": ""}),
                _db(), owner_id="owner-1",
            )


async def test_update_que_troca_o_tipo_deixa_so_os_campos_do_novo():
    """De postgresql para authkey: host/user/password e a DSN antiga não ficam
    cifrados no blob de uma credencial de outro tipo (o resolver tinha de
    aprender a ignorá-los)."""
    cred = _cred_pg()
    with _patch_get(cred), _patch_cripto()[0], _patch_cripto()[1]:
        out = await svc.update_credential(
            uuid4(), CredentialUpdate(name="n", type="geoserver_authkey", data={"token": "c0ffee-SEGREDO-42"}),
            _db(), owner_id="owner-1",
        )
    assert _dec(out.data) == {"token": "c0ffee-SEGREDO-42"}


async def test_update_que_deixa_de_ser_de_banco_nao_arrasta_a_dsn():
    """postgresql → tipo livre: a DSN derivada (com a senha) não fica no blob,
    senão um nó de banco ainda a receberia; os outros campos ficam (um tipo
    livre não tem esquema para dizer quais valem)."""
    cred = _cred_pg()
    with _patch_get(cred), _patch_cripto()[0], _patch_cripto()[1]:
        out = await svc.update_credential(
            uuid4(), CredentialUpdate(name="n", type="tipo_custom", data={"outro": "novo"}), _db(), owner_id="owner-1",
        )
    dados = _dec(out.data)
    assert "connectionString" not in dados and dados["outro"] == "novo" and dados["host"] == "h"


async def test_valor_gravado_que_nao_e_string_nao_derruba_a_validacao():
    # A troca de tipo valida o `data` já gravado; uma porta numérica legada
    # não pode virar 500.
    assert svc.erro_de_validacao("postgresql", {"host": "h", "port": 5432, "database": "d", "user": "u", "password": "p"}) is None
    assert svc.erro_de_validacao("postgresql", {"host": 0, "database": "d", "user": "u", "password": "p"}) == "Campos obrigatórios ausentes: Host"


async def test_update_que_troca_o_tipo_sem_data_exige_os_campos_do_novo():
    """Trocar só o tipo, sem mandar os campos dele, gravaria uma credencial
    que nenhum nó consegue usar."""
    cred = _cred_pg()
    with _patch_get(cred), _patch_cripto()[0], _patch_cripto()[1]:
        with pytest.raises(CredentialValidationError, match="Chave"):
            await svc.update_credential(
                uuid4(), CredentialUpdate(name="n", type="geoserver_authkey"), _db(), owner_id="owner-1",
            )


# ── as regras do nó WFS valem ao gravar e ao Testar ──────────────────────────

async def test_create_recusa_o_que_o_no_wfs_recusaria():
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


def test_erro_de_validacao_e_a_mesma_regra_do_testar():
    assert svc.erro_de_validacao("geoserver_authkey", {"token": "c0ffee-SEGREDO-42"}) is None
    assert svc.erro_de_validacao("geoserver_authkey", {"token": ""}) == "Campos obrigatórios ausentes: Chave (authkey)"
    assert "cabeçalho" in svc.erro_de_validacao(
        "geoserver_authkey", {"token": "c0ffee-SEGREDO-42", "parameter": "Host", "location": "header"},
    )
    assert svc.erro_de_validacao("tipo_custom", {}) is None


# ── update: metadados PATCH-like ──────────────────────────────────────────────

async def test_update_omitir_metadado_preserva():
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


async def test_update_null_explicito_limpa():
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
    assert out.tags == ["a"]   # tags foi omitido → preservado


# ── list: escopo ──────────────────────────────────────────────────────────────

async def test_list_une_dono_e_compartilhadas():
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

def test_expires_at_property_deriva_de_data():
    c = Credential(name="c", type="webhook_token", data={"expires_at": "2027-05-01T00:00:00Z"})
    assert c.expires_at is not None and c.expires_at.year == 2027


def test_expires_at_property_ausente_ou_invalido():
    assert Credential(name="c", type="s3", data={"x": "y"}).expires_at is None
    assert Credential(name="c", type="s3", data={"expires_at": "lixo"}).expires_at is None
    assert Credential(name="c", type="s3", data=None).expires_at is None


def test_credential_out_preenche_expires_at_via_property():
    c = Credential(name="c", type="webhook_token", data={"expires_at": "2027-05-01T00:00:00Z"})
    c.id = uuid4()
    c.created_at = c.updated_at = datetime.utcnow()
    out = CredentialOut.model_validate(c)
    assert out.expires_at is not None and out.expires_at.year == 2027


def test_encrypt_and_store_sempre_cifra_valor_com_prefixo_gaaaa():
    """Auditoria SEG-19: um valor que o cliente envia começando com 'gAAAA'
    (o ciphertext de outra pessoa) NÃO pode ser gravado em claro — senão o
    GET /data o decifraria com a chave da plataforma (oráculo). Agora é sempre
    cifrado, e decifrar devolve a própria string 'gAAAA…', nunca um segredo."""
    from app.models.credential import Credential
    from app.core.utils.encryption import decrypt_credential_data

    falso_ciphertext = "gAAAAA-conteudo-cifrado-de-outra-pessoa"
    cred = Credential(type="http_bearer", name="x")
    cred.encrypt_and_store({"token": falso_ciphertext})
    # Foi cifrado (não ficou igual ao que entrou).
    assert cred.data["token"] != falso_ciphertext
    assert cred.data["token"].startswith("gAAAA")
    # E decifrar devolve a string original, não um segredo alheio.
    assert decrypt_credential_data(cred.data)["token"] == falso_ciphertext
