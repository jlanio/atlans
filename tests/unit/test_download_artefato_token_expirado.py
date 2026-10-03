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
def without_jwt(monkeypatch):
    """No Bearer is accepted as a JWT — forces the credential-token path."""
    async def _deny(*_a, **_k):
        return False
    monkeypatch.setattr(ar, "_jwt_has_workspace_access", _deny)


def _stub_credential(monkeypatch, token="segredo", expires_at=None):
    async def _resolve(*_a, **_k):
        return token, expires_at
    monkeypatch.setattr(ar, "_resolve_bearer_credential", _resolve)


# ── EXPIRA ───────────────────────────────────────────────────────────────────

async def test_expired_token_gets_403(monkeypatch, without_jwt):
    """The central regression: an expired token no longer downloads."""
    _stub_credential(monkeypatch, expires_at=_iso(timedelta(hours=-1)))

    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)

    assert exc.value.status_code == 403
    assert "expirado" in exc.value.detail.lower()


async def test_valid_token_within_validity_downloads(monkeypatch, without_jwt):
    _stub_credential(monkeypatch, expires_at=_iso(timedelta(hours=1)))
    await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)


async def test_naive_expiration_is_treated_as_utc(monkeypatch, without_jwt):
    """An expires_at without a time zone must not become TypeError -> 500 in authorization."""
    naive = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).replace(tzinfo=None).isoformat()
    _stub_credential(monkeypatch, expires_at=naive)

    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)
    assert exc.value.status_code == 403


def test_invalid_expires_at_format_is_500():
    """Same semantics as _validate_webhook_token: a broken format does not grant access."""
    with pytest.raises(HTTPException) as exc:
        ar._reject_if_token_expired("nao-e-uma-data")
    assert exc.value.status_code == 500


# ── NO FIELD ─────────────────────────────────────────────────────────────────

async def test_credential_without_expires_at_still_downloads(monkeypatch, without_jwt):
    _stub_credential(monkeypatch, expires_at=None)
    await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)


def test_empty_expires_at_does_not_reject():
    ar._reject_if_token_expired(None)
    ar._reject_if_token_expired("")


# ── ORDEM ────────────────────────────────────────────────────────────────────

async def test_member_jwt_takes_priority_and_does_not_query_credential(monkeypatch):
    """A valid JWT grants access without touching the credential — even if it is expired."""
    async def _allow(*_a, **_k):
        return True
    monkeypatch.setattr(ar, "_jwt_has_workspace_access", _allow)

    async def _explode(*_a, **_k):
        raise AssertionError("JWT valido nao pode consultar a credencial")
    monkeypatch.setattr(ar, "_resolve_bearer_credential", _explode)

    await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer jwt-valido"), None)


async def test_artifact_without_credential_is_public(monkeypatch):
    """Without a credential_id there is nothing to authorize — not even a header is required."""
    await ar._autorizar_download(_FakeArtifact(credential_id=None), _FakeRequest(), None)


async def test_without_authorization_header_is_401(without_jwt):
    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest(), None)
    assert exc.value.status_code == 401


async def test_different_token_is_401(monkeypatch, without_jwt):
    _stub_credential(monkeypatch, token="segredo")
    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer errado"), None)
    assert exc.value.status_code == 401


async def test_unresolvable_credential_is_401(monkeypatch, without_jwt):
    """A missing/unreadable credential must not turn into granted access."""
    _stub_credential(monkeypatch, token=None)
    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer qualquer"), None)
    assert exc.value.status_code == 401


# ── UM SO LUGAR ──────────────────────────────────────────────────────────────

def test_the_endpoint_uses_the_single_helper():
    """Prevents the authorization block from being copied inline again."""
    fonte = inspect.getsource(ar.download_artifact)
    assert "_autorizar_download" in fonte, (
        "download_artifact precisa delegar a autorizacao a _autorizar_download"
    )
    assert "compare_digest" not in fonte, (
        "download_artifact nao pode comparar o token inline — use _autorizar_download"
    )
