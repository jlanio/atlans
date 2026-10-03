# tests/unit/test_download_artefato_token_expirado.py
"""
Token expiry on public artifact downloads.

The pair of public endpoints `/artifacts/{id_hash}/download` and
`/artifacts/runs/{run_id}/{filename}` (the latter was removed later, having no
client) compared the received Bearer with the `webhook_token` credential's token
and NEVER read `expires_at`. Triggering the webhook was
refused after expiry (`_validate_webhook_token` checks), but the download kept
working — shortening the token's validity revoked one thing and not the
other.

These tests lock four properties:

  EXPIRES       an expired token gets 403, not 200.

  ORDER         the workspace member's JWT still takes priority over the
                token, and a valid JWT does not query the credential. Swapping
                that order would break access for the authenticated UI.

  NO FIELD      a credential without `expires_at` still downloads — the field
                is optional and most credentials do not fill it in.

  ONE PLACE     the endpoint delegates to the helper. The divergence between
                the two copies is what let the hole through; if someone
                reintroduces the inline block, this test fails.
"""
import inspect
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.api.routers import artifacts_router as ar


# ── Fakes ────────────────────────────────────────────────────────────────────

class _FakeArtifact:
    def __init__(self, credential_id="cred-1", workspace_id="ws-1"):
        self.credential_id = credential_id
        self.workspace_id = workspace_id
        self.id_hash = "art-1"
        self.filename = "saida.geojson"
        self.run_id = "run-1"
        self.s3_key = "artifacts/ws-1/run-1/saida.geojson"


class _FakeRequest:
    def __init__(self, authorization=None):
        self.headers = {"Authorization": authorization} if authorization else {}


def _iso(delta: timedelta) -> str:
    return (datetime.now(tz=timezone.utc) + delta).isoformat()


@pytest.fixture
def sem_jwt(monkeypatch):
    """No Bearer is accepted as a JWT — forces the credential-token path."""
    async def _nao(*_a, **_k):
        return False
    monkeypatch.setattr(ar, "_jwt_has_workspace_access", _nao)


def _credencial(monkeypatch, token="segredo", expires_at=None):
    async def _resolve(*_a, **_k):
        return token, expires_at
    monkeypatch.setattr(ar, "_resolve_bearer_credential", _resolve)


# ── EXPIRA ───────────────────────────────────────────────────────────────────

async def test_token_expirado_recebe_403(monkeypatch, sem_jwt):
    """The central regression: an expired token no longer downloads."""
    _credencial(monkeypatch, expires_at=_iso(timedelta(hours=-1)))

    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)

    assert exc.value.status_code == 403
    assert "expirado" in exc.value.detail.lower()


async def test_token_valido_dentro_da_validade_baixa(monkeypatch, sem_jwt):
    _credencial(monkeypatch, expires_at=_iso(timedelta(hours=1)))
    await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)


async def test_expiracao_ingenua_e_tratada_como_utc(monkeypatch, sem_jwt):
    """An expires_at without a time zone must not become TypeError -> 500 in authorization."""
    ingenuo = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).replace(tzinfo=None).isoformat()
    _credencial(monkeypatch, expires_at=ingenuo)

    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)
    assert exc.value.status_code == 403


def test_formato_invalido_de_expires_at_e_500():
    """Same semantics as _validate_webhook_token: a broken format does not grant access."""
    with pytest.raises(HTTPException) as exc:
        ar._recusar_se_token_expirado("nao-e-uma-data")
    assert exc.value.status_code == 500


# ── NO FIELD ─────────────────────────────────────────────────────────────────

async def test_credencial_sem_expires_at_continua_baixando(monkeypatch, sem_jwt):
    _credencial(monkeypatch, expires_at=None)
    await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)


def test_expires_at_vazio_nao_recusa():
    ar._recusar_se_token_expirado(None)
    ar._recusar_se_token_expirado("")


# ── ORDEM ────────────────────────────────────────────────────────────────────

async def test_jwt_de_membro_tem_prioridade_e_nao_consulta_credencial(monkeypatch):
    """A valid JWT grants access without touching the credential — even if it is expired."""
    async def _sim(*_a, **_k):
        return True
    monkeypatch.setattr(ar, "_jwt_has_workspace_access", _sim)

    async def _explode(*_a, **_k):
        raise AssertionError("JWT valido nao pode consultar a credencial")
    monkeypatch.setattr(ar, "_resolve_bearer_credential", _explode)

    await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer jwt-valido"), None)


async def test_artefato_sem_credencial_e_publico(monkeypatch):
    """Without a credential_id there is nothing to authorize — not even a header is required."""
    await ar._autorizar_download(_FakeArtifact(credential_id=None), _FakeRequest(), None)


async def test_sem_header_authorization_e_401(sem_jwt):
    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest(), None)
    assert exc.value.status_code == 401


async def test_token_diferente_e_401(monkeypatch, sem_jwt):
    _credencial(monkeypatch, token="segredo")
    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer errado"), None)
    assert exc.value.status_code == 401


async def test_credencial_irresolvivel_e_401(monkeypatch, sem_jwt):
    """A missing/unreadable credential must not turn into granted access."""
    _credencial(monkeypatch, token=None)
    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer qualquer"), None)
    assert exc.value.status_code == 401


# ── UM SO LUGAR ──────────────────────────────────────────────────────────────

def test_o_endpoint_usa_o_helper_unico():
    """Prevents the authorization block from being copied inline again."""
    fonte = inspect.getsource(ar.download_artifact)
    assert "_autorizar_download" in fonte, (
        "download_artifact precisa delegar a autorizacao a _autorizar_download"
    )
    assert "compare_digest" not in fonte, (
        "download_artifact nao pode comparar o token inline — use _autorizar_download"
    )
