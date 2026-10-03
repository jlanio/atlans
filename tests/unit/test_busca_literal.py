"""Substring search: the user's term is LITERAL, on every screen.

The escaping of `%` and `_` was copied by hand into four services (artifacts,
Drive, sources, runs) and forgotten in the fifth: the admin's user search built
a raw `f"%{search}%"`. There the term's `_` became a wildcard — searching for
"a_b" also returned "aXb", and "___" matched any account —, the same defect the
comment in `artifact_service._filtros` describes and that the other copies had
already fixed. Real database (SQLite), as in `test_drive_busca_escape.py`: what
matters is the behavior of LIKE.
"""
from pathlib import Path

import pytest_asyncio
from sqlalchemy import column
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.utils.busca import contem, escapar_like
from app.models.user import User
from app.services import admin_user_service

RAIZ = Path(__file__).resolve().parents[2]


@pytest_asyncio.fixture
async def db():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=[User.__table__])
    async with AsyncSession(eng, expire_on_commit=False) as sessao:
        yield sessao
    await eng.dispose()


async def _semear(db, *nomes):
    for i, nome in enumerate(nomes):
        db.add(User(
            id_hash=f"u-{i}", username=nome, email=f"conta{i}@exemplo.test",
            hashed_password="x",
        ))
    await db.commit()


async def test_sublinhado_na_busca_de_usuarios_e_literal(db):
    # `aXb` matches the PATTERN `a_b` if `_` is a wildcard, and does not if it is literal.
    await _semear(db, "aXb", "a_b")

    usuarios, total = await admin_user_service.list_users(db, search="a_b")

    assert total == 1, "o sublinhado da busca de usuários é curinga"
    assert [u.username for u in usuarios] == ["a_b"]


async def test_porcento_na_busca_de_usuarios_e_literal(db):
    await _semear(db, "100X", "100%")

    usuarios, total = await admin_user_service.list_users(db, search="100%")

    assert total == 1, "o porcento da busca de usuários é curinga"
    assert [u.username for u in usuarios] == ["100%"]


async def test_sublinhados_sozinhos_nao_listam_a_base_inteira(db):
    await _semear(db, "ana", "bia", "caio")

    _, total = await admin_user_service.list_users(db, search="___")

    assert total == 0


async def test_busca_de_usuarios_segue_sem_diferenciar_caixa(db):
    """Escaping must not cost the ILIKE: "ANA" still finds "ana"."""
    await _semear(db, "ana", "bia")

    usuarios, total = await admin_user_service.list_users(db, search="ANA")

    assert total == 1 and usuarios[0].username == "ana"


# ── The single piece ─────────────────────────────────────────────────────────

def test_escape_cobre_a_barra_antes_dos_curingas():
    # The user's `\` is escaped first: otherwise "a\_b" would become "a\\_b", and
    # the `_` would be a wildcard again after a literal backslash.
    assert escapar_like("a\\_b%") == "a\\\\\\_b\\%"


def test_contem_e_ilike_com_escape_explicito():
    compilado = contem(column("nome"), "a_b").compile(dialect=postgresql.dialect())

    assert "ILIKE" in str(compilado) and "ESCAPE" in str(compilado)
    assert list(compilado.params.values()) == ["%a\\_b%"]


def test_contem_sem_ignorar_caixa_e_like_simples():
    """The sources' `busca` column is stored normalized: LIKE is enough."""
    sql = str(contem(column("busca"), "saude", ignorar_caixa=False).compile(dialect=postgresql.dialect()))

    assert " LIKE " in sql and "ILIKE" not in sql
    assert "ESCAPE" in sql


def test_o_escape_do_like_mora_num_lugar_so():
    """Each copy of the escaping was a chance to forget it — and the user search
    forgot. Every substring search goes through `contem`."""
    copias = []
    for caminho in sorted((RAIZ / "app").rglob("*.py")):
        rel = caminho.relative_to(RAIZ).as_posix()
        if rel == "app/core/utils/busca.py":
            continue
        for n, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
            if ".ilike(" in linha or '.replace("%", ' in linha or ".replace('%', " in linha:
                copias.append(f"{rel}:{n} — {linha.strip()}")

    assert not copias, (
        "busca por substring montada à mão; use app.core.utils.busca.contem:\n  "
        + "\n  ".join(copias)
    )
