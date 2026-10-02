# tests/unit/test_download_artefato_token_expirado.py
"""
Expiracao do token nos downloads publicos de artefato.

O par de endpoints publicos `/artifacts/{id_hash}/download` e
`/artifacts/runs/{run_id}/{filename}` (este saiu depois, sem cliente) comparava o
Bearer recebido com o token da credencial `webhook_token` e NUNCA lia
`expires_at`. O disparo do webhook era
recusado depois do vencimento (`_validate_webhook_token` checa), mas o download
seguia funcionando — encurtar a validade do token revogava uma coisa e nao a
outra.

Estes testes travam quatro propriedades:

  EXPIRA        token vencido recebe 403, nao 200.

  ORDEM         o JWT de membro do workspace continua tendo prioridade sobre o
                token, e um JWT valido nao consulta a credencial. Trocar essa
                ordem quebraria o acesso da UI autenticada.

  SEM CAMPO     credencial sem `expires_at` continua baixando — o campo e
                opcional e a maioria das credenciais nao o preenche.

  UM SO LUGAR   o endpoint delega ao helper. A divergencia entre as duas
                copias foi o que deixou o furo passar; se alguem
                reintroduzir o bloco inline, este teste cai.
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
    """Nenhum Bearer e aceito como JWT — forca o caminho do token da credencial."""
    async def _nao(*_a, **_k):
        return False
    monkeypatch.setattr(ar, "_jwt_has_workspace_access", _nao)


def _credencial(monkeypatch, token="segredo", expires_at=None):
    async def _resolve(*_a, **_k):
        return token, expires_at
    monkeypatch.setattr(ar, "_resolve_bearer_credential", _resolve)


# ── EXPIRA ───────────────────────────────────────────────────────────────────

async def test_token_expirado_recebe_403(monkeypatch, sem_jwt):
    """A regressao central: token vencido nao baixa mais."""
    _credencial(monkeypatch, expires_at=_iso(timedelta(hours=-1)))

    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)

    assert exc.value.status_code == 403
    assert "expirado" in exc.value.detail.lower()


async def test_token_valido_dentro_da_validade_baixa(monkeypatch, sem_jwt):
    _credencial(monkeypatch, expires_at=_iso(timedelta(hours=1)))
    await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)


async def test_expiracao_ingenua_e_tratada_como_utc(monkeypatch, sem_jwt):
    """Um expires_at sem timezone nao pode virar TypeError -> 500 na autorizacao."""
    ingenuo = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).replace(tzinfo=None).isoformat()
    _credencial(monkeypatch, expires_at=ingenuo)

    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)
    assert exc.value.status_code == 403


def test_formato_invalido_de_expires_at_e_500():
    """Mesma semantica de _validate_webhook_token: formato quebrado nao libera."""
    with pytest.raises(HTTPException) as exc:
        ar._recusar_se_token_expirado("nao-e-uma-data")
    assert exc.value.status_code == 500


# ── SEM CAMPO ────────────────────────────────────────────────────────────────

async def test_credencial_sem_expires_at_continua_baixando(monkeypatch, sem_jwt):
    _credencial(monkeypatch, expires_at=None)
    await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer segredo"), None)


def test_expires_at_vazio_nao_recusa():
    ar._recusar_se_token_expirado(None)
    ar._recusar_se_token_expirado("")


# ── ORDEM ────────────────────────────────────────────────────────────────────

async def test_jwt_de_membro_tem_prioridade_e_nao_consulta_credencial(monkeypatch):
    """JWT valido libera sem tocar na credencial — inclusive se ela estiver vencida."""
    async def _sim(*_a, **_k):
        return True
    monkeypatch.setattr(ar, "_jwt_has_workspace_access", _sim)

    async def _explode(*_a, **_k):
        raise AssertionError("JWT valido nao pode consultar a credencial")
    monkeypatch.setattr(ar, "_resolve_bearer_credential", _explode)

    await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer jwt-valido"), None)


async def test_artefato_sem_credencial_e_publico(monkeypatch):
    """Sem credential_id nao ha o que autorizar — nem header e exigido."""
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
    """Credencial ausente/ilegivel nao pode virar acesso liberado."""
    _credencial(monkeypatch, token=None)
    with pytest.raises(HTTPException) as exc:
        await ar._autorizar_download(_FakeArtifact(), _FakeRequest("Bearer qualquer"), None)
    assert exc.value.status_code == 401


# ── UM SO LUGAR ──────────────────────────────────────────────────────────────

def test_o_endpoint_usa_o_helper_unico():
    """Impede que o bloco de autorizacao volte a ser copiado inline."""
    fonte = inspect.getsource(ar.download_artifact)
    assert "_autorizar_download" in fonte, (
        "download_artifact precisa delegar a autorizacao a _autorizar_download"
    )
    assert "compare_digest" not in fonte, (
        "download_artifact nao pode comparar o token inline — use _autorizar_download"
    )
