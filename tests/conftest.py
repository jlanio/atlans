# tests/conftest.py
"""
Fixtures compartilhadas entre todos os testes.
"""
import os
import pytest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

# Garante que variáveis de ambiente críticas existam antes de importar os módulos da app
os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-minimum!!")
os.environ.setdefault("APP_SECRET", "test-app-secret-for-unit-tests!!")
os.environ.setdefault("FERNET_KEY", "aTjxua8UQDFu3W4os-o9LeGQ9P_pv58w0I6xuzSdnQE=")
# executor/config.py levanta ValueError no import se EXECUTOR_ID nao existir.
# Sem isto, qualquer teste que importe executor.* passa na maquina de quem tem
# executor/.env configurado e quebra na coleta do CI.
os.environ.setdefault("EXECUTOR_ID", "executor-test-0000")
# Um fuso padrão de agendamento DIFERENTE de UTC, de propósito: é o único jeito
# de os testes distinguirem "o padrão configurado" (AGENDAMENTO_FUSO_PADRAO) do
# UTC que o `datetime` daria por acidente. O padrão do código é UTC. UTC-4 o
# ano inteiro (sem horário de verão): o resultado não muda com a data da rodada.
os.environ.setdefault("AGENDAMENTO_FUSO_PADRAO", "America/La_Paz")
# O limiter global da suite conta em memoria, sempre. Sem isto ele usaria o
# REDIS_URL — que existe no container de dev — ou um RATE_LIMIT_STORAGE_URI
# de um .env de dev, e rodaria contra o Redis de verdade, com contadores que
# sobrevivem entre as rodadas (o bucket de 60/hora do editor enche em tres
# rodadas). Quem testa o storage constroi o proprio limiter.
os.environ["RATE_LIMIT_STORAGE_URI"] = "memory://"


# ── Isolamento do logging ──────────────────────────────────────────────────────

# A fábrica de LogRecord como o processo nasceu, capturada ANTES da coleta: os
# módulos de teste que importam `executor.main` no topo já a trocam durante a
# coleta (o módulo chama `configure_logging()` no import).
import logging as _logging

_FABRICA_ORIGINAL = _logging.getLogRecordFactory()


def _fabrica_limpa() -> None:
    from flow.utils import redacao_log, segredos_vivos

    _logging.setLogRecordFactory(_FABRICA_ORIGINAL)
    # `segredos_vivos` se instala uma vez e lembra que instalou: a flag volta
    # junto, senão ele nunca se reinstalaria na fábrica limpa.
    redacao_log._instalada = False
    segredos_vivos._instalada = False


@pytest.fixture(autouse=True)
def _fabrica_de_logrecord_isolada():
    """A redação de segredos do executor mora na fábrica de LogRecord do
    PROCESSO (`flow.utils.redacao_log.instalar_no_processo`). Sem este reset,
    um import de `executor.main` a deixaria ligada para a suíte inteira, e quem
    confere o `***` de `segredos_vivos` (ou um prefixo de token numa linha de
    auditoria) veria `<REDACTED>` conforme a ordem da suíte. Quem testa a
    redação a instala dentro do próprio teste."""
    _fabrica_limpa()
    yield
    _fabrica_limpa()


# ── Extensões ─────────────────────────────────────────────────────────────────


@pytest.fixture
def registro_de_teste(monkeypatch):
    """Um registro de extensões VAZIO no lugar do de verdade (app/extensoes).

    É o núcleo sozinho, como na distribuição livre — e o teste pendura nele só
    o que quiser (um `plano_e_teto` de mentira, uma contribuição ao painel).
    As rotas que o app já incluiu continuam; troca-se o que o núcleo consulta
    a cada pedido.
    """
    from app import extensoes

    novo = extensoes.Registro()
    monkeypatch.setattr(extensoes, "_registro", novo)
    return novo


# ── Mocks de infraestrutura ────────────────────────────────────────────────────


@pytest.fixture
def mock_redis():
    """Mock do cliente Redis assíncrono (idempotência)."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.lpush = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    redis.aclose = AsyncMock()
    return redis


@pytest.fixture
def mock_current_user():
    """Usuário autenticado fictício para injeção via dependency_overrides."""
    user = MagicMock()
    user.id_hash = "usr-test-001"
    user.is_active = True
    user.role = "user"
    return user


@pytest.fixture
def mock_workspace_ids():
    """Lista de workspace IDs acessíveis ao usuário de teste."""
    return ["ws-test-001"]


@pytest.fixture
async def client(mock_redis, mock_current_user, mock_workspace_ids):
    """
    AsyncClient com a app real e toda a infra (Redis, DB, MinIO, scheduler) mockada.
    Autentica automaticamente como mock_current_user no workspace ws-test-001.
    """
    from httpx import AsyncClient, ASGITransport

    from app.main import app
    from app.api.dependencies import get_current_user, get_user_workspace_ids

    async def _current_user():
        return mock_current_user

    async def _workspace_ids():
        return mock_workspace_ids

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_user_workspace_ids] = _workspace_ids

    mock_sched = MagicMock()
    mock_sched.start = AsyncMock()
    mock_sched.stop = AsyncMock()

    with ExitStack() as stack:
        stack.enter_context(patch("app.main._wait_for_db", new_callable=AsyncMock))
        # Pool Redis centralizado: injeta o mock diretamente no módulo redis.py
        stack.enter_context(patch("app.core.redis._pool", mock_redis))
        stack.enter_context(patch("app.core.redis.init_redis", AsyncMock(return_value=mock_redis)))
        stack.enter_context(patch("app.core.redis.close_redis", AsyncMock()))
        stack.enter_context(patch("app.core.storage.ensure_bucket"))
        stack.enter_context(patch("app.core.run_result_consumer.run_consumer_loop", new_callable=AsyncMock))
        stack.enter_context(patch("app.core.artifact_cleanup.run_cleanup_loop", new_callable=AsyncMock))
        stack.enter_context(patch("app.core.fontes_catalogo.importar_catalogo_no_arranque", new_callable=AsyncMock))
        stack.enter_context(patch("app.core.fontes_catalogo.run_verificacao_loop", new_callable=AsyncMock))
        stack.enter_context(patch("app.core.async_scheduler.scheduler", mock_sched))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


