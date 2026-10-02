# tests/unit/test_change_detector_router.py
"""Testes do router /internal/change-detector — bridge HTTP do executor para
o Redis do servidor onde o ChangeDetector armazena hashes."""
import pytest
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

@contextmanager
def _bypass_auth_and_db(*, workflow_workspace_id: str | None = "ws-test-001"):
    """Substitui _auth_agent e get_db (não há DB real nos testes unitários).

    O router real chama `_auth_agent` do drive_router, que autentica o executor
    pelo cert mTLS. Para testes unitários do router em si, basta simular sucesso
    de auth e usar uma session mock.

    `_authorize_key` consulta o banco para descobrir a que workspace pertence o
    workflow de uma chave `wf:*`. O DB mock devolve `workflow_workspace_id` —
    passe um valor fora de `_resolved_ws_ids` (ou None) para exercitar o 403.
    """
    from app.main import app
    from app.api.dependencies import get_db

    async def _fake_db():
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=workflow_workspace_id)
        db.execute = AsyncMock(return_value=result)
        yield db

    fake_agent = MagicMock()
    fake_agent.id_hash = "executor-test-001"
    fake_agent._resolved_ws_ids = ["ws-test-001"]

    app.dependency_overrides[get_db] = _fake_db
    auth_patch = patch(
        "app.api.routers.change_detector_router._auth_agent",
        new_callable=AsyncMock,
        return_value=fake_agent,
    )
    auth_patch.start()
    try:
        yield
    finally:
        auth_patch.stop()
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def fake_redis():
    """Cliente Redis fake que armazena chaves em dict in-memory."""
    store = {}
    ttls = {}

    rc = AsyncMock()

    async def _get(key):
        return store.get(key)

    async def _set(key, value, ex=None, get=False):
        anterior = store.get(key)
        store[key] = value if isinstance(value, str) else value.decode()
        if ex is None:
            ttls.pop(key, None)
        else:
            ttls[key] = ex
        return anterior if get else True

    async def _setex(key, ttl, value):
        store[key] = value if isinstance(value, str) else value.decode()
        ttls[key] = ttl
        return True

    async def _ttl(key):
        if key not in store:
            return -2
        return ttls.get(key, -1)

    class _Pipe:
        """Pipeline fake: enfileira get/ttl (sync) e executa na ordem (async)."""
        def __init__(self):
            self._ops = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return False

        def get(self, key):
            self._ops.append(("get", key))
            return self

        def ttl(self, key):
            self._ops.append(("ttl", key))
            return self

        async def execute(self):
            saidas = []
            for op, key in self._ops:
                saidas.append(await (_get(key) if op == "get" else _ttl(key)))
            return saidas

    rc.get = _get
    rc.set = _set
    rc.setex = _setex
    rc.ttl = _ttl
    rc.pipeline = lambda *a, **k: _Pipe()
    rc._store = store
    rc._ttls = ttls
    return rc


# ── SWAP (POST) ───────────────────────────────────────────────────────────────

SWAP_URL = "/internal/change-detector/wf:wfh-abc:n-xyz"


@pytest.mark.asyncio
async def test_swap_primeira_vez_devolve_previous_none_e_grava(client, fake_redis):
    payload = {"hash": "c" * 64, "ttl_seconds": 7200}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 200
    assert resp.json()["previous_hash"] is None
    assert fake_redis._store["change_detector:wf:wfh-abc:n-xyz"] == "c" * 64
    assert fake_redis._ttls["change_detector:wf:wfh-abc:n-xyz"] == 7200


@pytest.mark.asyncio
async def test_swap_devolve_o_anterior_e_grava_o_novo(client, fake_redis):
    """A operação única: decisão (previous) e gravação (novo) na mesma ida —
    sem a janela ler→decidir→gravar em que duas runs simultâneas liam o mesmo
    hash antigo e ambas decidiam 'Mudou'."""
    fake_redis._store["change_detector:wf:wfh-abc:n-xyz"] = "a" * 64
    payload = {"hash": "b" * 64, "ttl_seconds": 3600}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 200
    assert resp.json()["previous_hash"] == "a" * 64
    assert fake_redis._store["change_detector:wf:wfh-abc:n-xyz"] == "b" * 64


@pytest.mark.asyncio
async def test_swap_sem_ttl_grava_sem_expiracao(client, fake_redis):
    payload = {"hash": "d" * 64, "ttl_seconds": 0}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 200
    assert "change_detector:wf:wfh-abc:n-xyz" in fake_redis._store
    assert "change_detector:wf:wfh-abc:n-xyz" not in fake_redis._ttls


@pytest.mark.asyncio
async def test_swap_hash_invalido_retorna_422(client, fake_redis):
    """Hash que não é SHA-256 hex (64 chars lowercase) é rejeitado."""
    payload = {"hash": "nao-eh-sha256", "ttl_seconds": 3600}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_swap_ttl_negativo_retorna_422(client, fake_redis):
    payload = {"hash": "e" * 64, "ttl_seconds": -1}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_swap_ttl_excessivo_retorna_422(client, fake_redis):
    payload = {"hash": "f" * 64, "ttl_seconds": 99_999_999}  # > 1 ano
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_swap_formato_chave_invalido_retorna_400(client, fake_redis):
    """Chaves fora do prefixo permitido (wf:/ws:) são rejeitadas."""
    payload = {"hash": "a" * 64, "ttl_seconds": 0}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post("/internal/change-detector/idempotency:abc", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_swap_redis_indisponivel_retorna_503(client):
    """Falha ao conectar com Redis → 503; o executor decide o branch pela
    política on_backend_error do nó."""
    redis_falho = AsyncMock()
    redis_falho.set = AsyncMock(side_effect=ConnectionError("redis down"))
    payload = {"hash": "a" * 64, "ttl_seconds": 0}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=redis_falho):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 503


# ── Escopo (cross-tenant) ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workflow_de_outro_workspace_retorna_403(client, fake_redis):
    """Executor não pode tocar o estado de um workflow fora dos seus workspaces:
    a troca fora de escopo é barrada ANTES de tocar o Redis."""
    fake_redis._store["change_detector:wf:wfh-alheio:n-xyz"] = "h" * 64
    with _bypass_auth_and_db(workflow_workspace_id="ws-de-outro-tenant"), \
            patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post("/internal/change-detector/wf:wfh-alheio:n-xyz",
                                 json={"hash": "a" * 64, "ttl_seconds": 0})
    assert resp.status_code == 403
    assert fake_redis._store["change_detector:wf:wfh-alheio:n-xyz"] == "h" * 64


@pytest.mark.asyncio
async def test_workflow_inexistente_retorna_403(client, fake_redis):
    """Não distingue 'não existe' de 'não é seu' — evita enumeração."""
    with _bypass_auth_and_db(workflow_workspace_id=None), \
            patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post("/internal/change-detector/wf:nao-existe:n-xyz",
                                 json={"hash": "a" * 64, "ttl_seconds": 0})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_escopo_ws_alheio_retorna_403(client, fake_redis):
    """Chave 'ws:' de workspace fora da lista do executor é negada."""
    with _bypass_auth_and_db(), \
            patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post("/internal/change-detector/ws:ws-alheio:shared-key",
                                 json={"hash": "a" * 64, "ttl_seconds": 0})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_escopo_ws_proprio_permitido(client, fake_redis):
    fake_redis._store["change_detector:ws:ws-test-001:shared-key"] = "i" * 64
    with _bypass_auth_and_db(), \
            patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post("/internal/change-detector/ws:ws-test-001:shared-key",
                                 json={"hash": "e" * 64, "ttl_seconds": 0})
    assert resp.status_code == 200
    assert resp.json()["previous_hash"] == "i" * 64


@pytest.mark.asyncio
async def test_swap_e_uma_unica_operacao_atomica(client):
    """A atomicidade não é observável num fake serializado, então este teste
    trava o PADRÃO: a troca inteira deve ser um único SET ... GET. Um GET
    separado seguido de SET reabriria exatamente a janela de corrida (duas runs
    simultâneas lendo o mesmo hash antigo) que o endpoint existe para fechar."""
    chamadas: list = []
    rc = AsyncMock()

    async def _set(key, value, ex=None, get=False):
        chamadas.append(("set", bool(get)))
        return None

    rc.set = _set
    rc.get = AsyncMock(side_effect=AssertionError("GET separado reabre a corrida"))

    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=rc):
        resp = await client.post(SWAP_URL, json={"hash": "a" * 64, "ttl_seconds": 60})

    assert resp.status_code == 200
    assert chamadas == [("set", True)]
