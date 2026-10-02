# tests/unit/_painel_do_modelo.py
"""O que os testes do painel do modelo (núcleo e extensões) dividem: o banco em
memória atrás da API e o catálogo e a sonda do provedor dublados."""
from contextlib import ExitStack, asynccontextmanager
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.system_config import SystemConfig
from app.models.uso_do_assistente import UsoDoAssistente
from tests.unit._mcp_harness import TABELAS_DAS_EXTENSOES

# A configuração (o modelo) e o uso medido; com os planos, as tabelas deles,
# que o custo por plano consulta.
TABELAS = [SystemConfig.__table__, UsoDoAssistente.__table__, *TABELAS_DAS_EXTENSOES]

CATALOGO = [
    {"id": "a/barato", "nome": "Barato", "entrada_por_milhao": 1.0,
     "saida_por_milhao": 5.0, "contexto": 100000},
    {"id": "a/caro", "nome": "Caro", "entrada_por_milhao": 15.0,
     "saida_por_milhao": 75.0, "contexto": 200000},
]


@asynccontextmanager
async def api_com_banco(client, usuario):
    """O cliente da API como admin, com o banco em memória no lugar do real.
    Cada arquivo de teste o embrulha na própria fixture `api`."""
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
    """O catálogo dublado e a SONDA dublada.

    A sonda faz uma chamada real ao provedor antes de salvar um modelo — é ela
    que impede a tela de aceitar um id que não funciona. Aqui ela é um no-op por
    padrão; `sonda=<exceção>` faz a recusa acontecer.
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
