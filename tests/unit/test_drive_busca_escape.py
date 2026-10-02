"""A busca do Drive escapa os curingas do LIKE (`%` e `_`).

Sem escapar, `list_files(search=...)` trata `_`/`%` do usuario como curinga e
varre a listagem inteira, dando a impressao de filtro quebrado — o mesmo defeito
que `artifact_service._filtros` ja consertou. Banco de verdade (SQLite, como em
`test_drive_teto_no_confirm.py`): o que importa e o comportamento do LIKE, e um
mock so diria que a chamada aconteceu.
"""
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.workspace_file import WorkspaceFile
from app.services.drive_service import DriveService

WS = "ws-1"


@pytest_asyncio.fixture
async def db():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(WorkspaceFile.metadata.create_all, tables=[WorkspaceFile.__table__])
    async with AsyncSession(eng, expire_on_commit=False) as sessao:
        yield sessao
    await eng.dispose()


async def _semear(db, *nomes):
    for i, nome in enumerate(nomes):
        db.add(WorkspaceFile(
            id_hash=f"f-{i}",
            workspace_id=WS,
            s3_key=f"drive/{WS}/{i}_{nome}",
            original_name=nome,
            extension=nome.rsplit(".", 1)[-1],
            size=10,
            uploaded_by="u-1",
            status="confirmed",
        ))
    await db.commit()


async def test_sublinhado_do_usuario_e_literal_e_nao_varre_tudo(db):
    # `aXb` casa o PADRAO `a_b` se o `_` for curinga, e nao casa se for literal.
    # E a linha que discrimina: sem ela, as duas versoes do codigo devolvem o
    # mesmo e o teste nao prova nada.
    await _semear(db, "aXb.geojson", "a_b.geojson")

    items, total = await DriveService(db).list_files(WS, search="a_b")

    assert total == 1, "o sublinhado voltou a ser curinga"
    assert items[0].original_name == "a_b.geojson"


async def test_porcento_do_usuario_tambem_e_literal(db):
    # `100X` casa `100%` com o `%` como curinga; so `100%` casa literal.
    await _semear(db, "100X.geojson", "100%.geojson")

    items, total = await DriveService(db).list_files(WS, search="100%")

    assert total == 1, "o porcento voltou a ser curinga"
    assert items[0].original_name == "100%.geojson"
