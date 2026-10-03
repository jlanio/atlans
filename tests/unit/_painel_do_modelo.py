# tests/unit/_painel_do_modelo.py
"""What the model panel tests (core and extensions) share: the in-memory
database behind the API and the stubbed provider catalog and probe."""
from contextlib import ExitStack, asynccontextmanager
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.system_config import SystemConfig
from app.models.uso_do_assistente import UsoDoAssistente
from tests.unit._mcp_harness import TABELAS_DAS_EXTENSOES

# The configuration (the model) and the measured usage; with the plans, their
# tables, which the per-plan cost queries.
TABELAS = [SystemConfig.__table__, UsoDoAssistente.__table__, *TABELAS_DAS_EXTENSOES]

CATALOGO = [
    {"id": "a/barato", "nome": "Barato", "entrada_por_milhao": 1.0,
     "saida_por_milhao": 5.0, "contexto": 100000},
    {"id": "a/caro", "nome": "Caro", "entrada_por_milhao": 15.0,
     "saida_por_milhao": 75.0, "contexto": 200000},
]


@asynccontextmanager
async def api_com_banco(client, usuario):
    """The API client as admin, with the in-memory database in place of the real
    one. Each test file wraps it in its own `api` fixture."""
    from app.api.dependencies import get_db
    from app.main import app

    usuario.role = "admin"
    usuario.username = "admin-test"

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as sessao:
        async def _db():
            yield sessao

        app.dependency_overrides[get_db] = _db
        try:
            yield client, sessao
        finally:
            app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


def com_catalogo(catalogo=CATALOGO, erro=None, sonda=None):
    """The stubbed catalog and the stubbed PROBE.

    The probe makes a real call to the provider before saving a model — it is
    what stops the screen from accepting an id that does not work. Here it is a
    no-op by default; `sonda=<exceção>` makes the refusal happen.
    """
    async def _listar(**kw):
        if erro is not None:
            raise erro
        return [dict(m) for m in catalogo]

    async def _sondar(modelo, **kw):
        if sonda is not None:
            raise sonda

    pilha = ExitStack()
    pilha.enter_context(patch("app.services.openrouter.listar_modelos", _listar))
    pilha.enter_context(patch("app.services.openrouter.sondar_modelo", _sondar))
    pilha.enter_context(patch("app.api.routers.admin_assistente_router.OPENROUTER_API_KEY", "k"))
    pilha.enter_context(patch("app.mcp.infra.redis_ou_none", lambda: None))
    return pilha
