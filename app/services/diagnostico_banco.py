"""
app/services/diagnostico_banco.py

`python -m app.cli check-db` (`make check-db`): checks DATABASE_URL the way the
API uses it — the same engine, driver (asyncpg) and TLS handling
(app/core/db.py) — and says in plain words what is wrong and how to fix it.

What it checks, in order:
  1. the connection and the login (host, port, pg_hba.conf, password, LDAP, TLS);
  2. the postgis and uuid-ossp extensions: installed, or whether this user can
     create them (the first migration runs CREATE EXTENSION IF NOT EXISTS, and
     PostGIS needs a superuser);
  3. the schema: whether `alembic upgrade head` already ran.

Only reads: it changes nothing in the database.
"""
from __future__ import annotations

import socket
from dataclasses import dataclass, field

EXTENSOES = ("postgis", "uuid-ossp")
COMANDO_DAS_EXTENSOES = (
    "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
)


@dataclass
class Relatorio:
    ok: bool = True
    linhas: list[str] = field(default_factory=list)

    def bom(self, texto: str) -> None:
        self.linhas.append(f"[ok]    {texto}")

    def aviso(self, texto: str) -> None:
        self.linhas.append(f"[aviso] {texto}")

    def falha(self, texto: str) -> None:
        self.ok = False
        self.linhas.append(f"[falha] {texto}")


def _cadeia(exc: BaseException):
    """The exception and what it wraps (SQLAlchemy's `orig`, `__cause__`, `__context__`)."""
    vistos: set[int] = set()
    fila = [exc]
    while fila:
        atual = fila.pop(0)
        if atual is None or id(atual) in vistos:
            continue
        vistos.add(id(atual))
        yield atual
        fila.extend([getattr(atual, "orig", None), atual.__cause__, atual.__context__])


def explicar_falha(exc: BaseException, onde: str) -> str:
    """What a connection failure means, in one or two sentences, with the fix.

    `onde` is `host:porta/banco`, already without the password.
    """
    for e in _cadeia(exc):
        nome = type(e).__name__
        texto = str(e)
        if "pg_hba.conf" in texto:
            return (
                f"O Postgres em {onde} recusou a conexao pelo pg_hba.conf: libere a rede do Docker "
                "(dentro de 172.16.0.0/12, por padrao) para esse banco e usuario, e recarregue o Postgres."
            )
        if "LDAP" in texto:
            return (
                f"O Postgres em {onde} autentica por LDAP, e o LDAP recusou o usuario: confira a senha, "
                "e se a conta nao esta bloqueada ou com a senha expirada no diretorio. Varias tentativas "
                "erradas seguidas podem bloquear a conta."
            )
        if nome in ("InvalidPasswordError", "InvalidAuthorizationSpecificationError") or "password authentication failed" in texto:
            return (
                f"O Postgres em {onde} recusou o login: confira usuario e senha no DATABASE_URL "
                "(uma senha com @ : / # % ? precisa ir codificada; o make bootstrap faz isso)."
            )
        if nome == "InvalidCatalogNameError" or ("database" in texto and "does not exist" in texto):
            return f"O banco nao existe em {onde}: crie-o (CREATE DATABASE ... OWNER <usuario>) ou corrija o nome."
        if isinstance(e, socket.gaierror) or "Name or service not known" in texto or "nodename nor servname" in texto:
            return (
                f"O host de {onde} nao resolve: corrija o nome. Postgres nesta mesma maquina e "
                "host.docker.internal, nao localhost."
            )
        if isinstance(e, ConnectionRefusedError) or "Connection refused" in texto or "Errno 111" in texto:
            if onde.split(":", 1)[0] in ("localhost", "127.0.0.1", "::1", "[::1]"):
                return (
                    f"Nada escuta em {onde}, e dentro do container localhost e o proprio container: "
                    "um Postgres nesta maquina e host.docker.internal no DATABASE_URL."
                )
            return (
                f"Nada escuta em {onde}: o Postgres esta de pe? Ele precisa ouvir na interface do Docker "
                "(listen_addresses) e nao so em localhost; confira tambem a porta e o firewall."
            )
        if isinstance(e, TimeoutError) or nome == "TimeoutError":
            return f"Sem resposta de {onde}: um firewall descartando a conexao, ou o host errado."
        if "SSL" in texto or "ssl" in nome.lower() or "certificate" in texto:
            return (
                f"Falha de TLS com {onde}: ajuste o ?ssl= do DATABASE_URL (require, verify-full) e, "
                "para verify-full, o DATABASE_CA_CERT."
            )
    return f"Nao foi possivel conectar em {onde}: {type(exc).__name__}: {exc}"


def _onde(url) -> str:
    return f"{url.host}:{url.port or 5432}/{url.database}"


async def diagnosticar() -> Relatorio:
    """Runs the checks with the API's own engine. Never raises: everything goes in the report."""
    from sqlalchemy import text
    from sqlalchemy.engine import make_url

    from app.core import db
    from app.core.config import DATABASE_URL

    rel = Relatorio()
    if not DATABASE_URL or db.async_engine is None:
        rel.falha("DATABASE_URL nao esta definida: rode o make bootstrap ou edite o .env.")
        return rel
    if "<usuario>" in DATABASE_URL:
        rel.falha("DATABASE_URL ainda e o exemplo do .env.example: rode o make bootstrap ou edite o .env.")
        return rel
    try:
        url = make_url(DATABASE_URL)
        onde = _onde(url)
    except Exception:  # noqa: BLE001 — a malformed URL is the finding itself
        rel.falha("DATABASE_URL nao e uma URL valida (postgresql+asyncpg://usuario:senha@host:5432/banco).")
        return rel

    try:
        async with db.async_engine.connect() as conn:
            versao = (await conn.execute(text("SHOW server_version"))).scalar_one()
            usuario, superusuario = (
                await conn.execute(text(
                    "SELECT current_user, rolsuper FROM pg_roles WHERE rolname = current_user"
                ))
            ).one()
            rel.bom(f"Conectado em {onde} como {usuario} (PostgreSQL {versao}).")

            instaladas = set((await conn.execute(text(
                "SELECT extname FROM pg_extension WHERE extname = ANY(:nomes)"
            ), {"nomes": list(EXTENSOES)})).scalars())
            disponiveis = set((await conn.execute(text(
                "SELECT name FROM pg_available_extensions WHERE name = ANY(:nomes)"
            ), {"nomes": list(EXTENSOES)})).scalars())
            migrado = (await conn.execute(text(
                "SELECT to_regclass('public.alembic_version') IS NOT NULL"
            ))).scalar_one()
            versao_schema = None
            if migrado:
                versao_schema = (await conn.execute(text(
                    "SELECT version_num FROM alembic_version LIMIT 1"
                ))).scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001 — the explanation is the output
        rel.falha(explicar_falha(exc, onde))
        return rel
    finally:
        await db.async_engine.dispose()

    faltando = [e for e in EXTENSOES if e not in instaladas]
    if not faltando:
        rel.bom("Extensoes postgis e uuid-ossp instaladas.")
    else:
        indisponiveis = [e for e in faltando if e not in disponiveis]
        if indisponiveis:
            rel.falha(
                f"O servidor nao tem a extensao {', '.join(indisponiveis)} instalada no sistema: "
                "instale o pacote (Debian/Ubuntu: postgresql-<versao>-postgis-3) no servidor do banco."
            )
        if superusuario:
            rel.aviso(
                f"Faltam {', '.join(faltando)}: a primeira migracao cria, porque {usuario} e superusuario."
            )
        elif not indisponiveis:
            rel.falha(
                f"Faltam {', '.join(faltando)}, e {usuario} nao e superusuario: a migracao vai parar em "
                f"'permission denied to create extension'. Uma vez, como superusuario:\n"
                f"          psql -d {url.database} -c '{COMANDO_DAS_EXTENSOES}'"
            )

    if versao_schema:
        rel.bom(f"Schema migrado (alembic {versao_schema}).")
    else:
        rel.aviso("Schema ainda nao criado: rode `alembic upgrade head` (veja o README).")
    return rel
