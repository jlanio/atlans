"""
Alembic env.py — environment configuration for Atlas Studio migrations.

Supports two modes:
  - offline: generates SQL without connecting to the database
  - online:  connects to the database and applies migrations directly

DATABASE_URL is read from the environment variable (or .env via python-dotenv).
The asyncpg driver is swapped for psycopg2 for compatibility with Alembic (synchronous).
"""
import os
import re
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url
from alembic import context
from dotenv import load_dotenv

# Ensure the project root is on sys.path so app.* can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

load_dotenv()

# Base and EVERY model, so the metadata is complete: the package imports each
# of its modules (and the extensions' models). A list here left eight tables
# out, and autogenerate proposed dropping them.
import app.models  # noqa: F401, E402
from app.models.base import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# PostGIS system tables — must not be managed by Alembic
_POSTGIS_TABLES = {
    "spatial_ref_sys",
    "layer",
    "topology",
    "geography_columns",
    "geometry_columns",
    "raster_columns",
    "raster_overviews",
}


def _include_object(obj, name, type_, reflected, compare_to):
    """Filters out objects Alembic must not manage."""
    if type_ == "table" and name in _POSTGIS_TABLES:
        return False
    return True


def _get_sync_url() -> str:
    """
    Returns DATABASE_URL converted to the synchronous driver (psycopg2).
    The ssl/sslmode parameter is moved to connect_args by `_connect_args`.
    """
    url = os.environ["DATABASE_URL"]
    # Swap the async driver for the sync one
    url = url.replace("+asyncpg", "+psycopg2").replace("postgresql://", "postgresql+psycopg2://")
    # Remove the asyncpg prefix without an explicit dialect
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
    return url


def run_migrations_offline() -> None:
    """Generates migration SQL without connecting to the database (useful for review/CI)."""
    url = _get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


_SSL_OFF = {"disable", "false", "0", "no", "allow"}
_SSL_VERIFY = {"verify-ca", "verify-full"}


def _bundle_do_sistema() -> str | None:
    """The system's CA bundle file, the one Python's `ssl` trusts by default."""
    import ssl

    caminhos = ssl.get_default_verify_paths()
    for candidato in (caminhos.cafile, caminhos.openssl_cafile, "/etc/ssl/certs/ca-certificates.crt"):
        if candidato and os.path.isfile(candidato):
            return candidato
    try:
        import certifi

        return certifi.where()
    except Exception:
        return None


def _raizes_confiaveis(ca_cert: str) -> str:
    """`sslrootcert` with the roots the API trusts (app/core/db.py): the
    system's, plus DATABASE_CA_CERT when that file exists.

    libpq takes ONE file and, without it, looks only at ~/.postgresql/root.crt:
    passing just DATABASE_CA_CERT (or nothing) made `alembic upgrade` refuse a
    server whose certificate the API — with the same URL — accepted (a public
    CA, a managed Postgres, an intermediate-only CA file). With a CA file, the
    two go together in a private temporary bundle."""
    sistema = _bundle_do_sistema()
    if ca_cert and os.path.isfile(ca_cert):
        if not sistema:
            return ca_cert
        import atexit
        import tempfile

        fd, combinado = tempfile.mkstemp(prefix="pg-roots-", suffix=".pem")
        with os.fdopen(fd, "wb") as destino:
            for origem in (sistema, ca_cert):
                with open(origem, "rb") as f:
                    destino.write(f.read().rstrip(b"\n") + b"\n")
        atexit.register(lambda: os.path.exists(combinado) and os.remove(combinado))
        return combinado
    # libpq 16+ reads "system" as the OpenSSL default store.
    return sistema or "system"


def _connect_args(url: str) -> tuple[str, dict]:
    """(URL without ssl/sslmode, psycopg2 connect_args) — the TLS of DATABASE_URL.

    The same reading as the API's engine (app/core/db.py, `_parse_url`):
      - no parameter                → nothing (libpq's default)
      - disable/false/0/no/allow    → sslmode=disable
      - verify-ca / verify-full     → the same mode, with the CA of
                                      DATABASE_CA_CERT as `sslrootcert`
      - require/prefer/true/1/...   → sslmode=require (encrypts, does not verify)

    verify-ca/verify-full used to become `require` here: the API refused a server
    with the wrong certificate and `alembic upgrade`, with the same URL, accepted
    it — a MITM got the migration connection, with the owner's credentials.
    The roots trusted are the API's (`_raizes_confiaveis`): the system's, plus
    DATABASE_CA_CERT when that file exists — the same URL connects in both.
    """
    connect_args: dict = {}
    match = re.search(r"[?&](?:ssl|sslmode)=([^&]+)", url)
    if not match:
        return url, connect_args

    raw_value = match.group(1).lower()
    # The parameter goes with the `&` after it, and its `?`/`&` stays: the next
    # parameter keeps a valid separator (`?ssl=x&a=b` -> `?a=b`).
    url = re.sub(r"([?&])(?:ssl|sslmode)=[^&]*&?", r"\1", url)
    url = url.rstrip("?&")

    if raw_value in _SSL_OFF:
        connect_args["sslmode"] = "disable"
    elif raw_value in _SSL_VERIFY:
        connect_args["sslmode"] = raw_value
        connect_args["sslrootcert"] = _raizes_confiaveis(os.getenv("DATABASE_CA_CERT", "").strip())
    else:
        connect_args["sslmode"] = "require"
    return url, connect_args


def _session_options(url: str) -> str:
    """libpq `options` for the migration session: the URL's own plus timezone=UTC.

    The same session time zone as the API (app/core/db.py, `_utc_session`): a
    `now()` that a migration writes into a TIMESTAMP column comes out in UTC, like
    the rows the API writes, whatever the server's `timezone`. connect_args
    replaces the URL's `options`, so those are carried over.
    """
    proprias = make_url(url).query.get("options", "")
    if isinstance(proprias, tuple):
        proprias = " ".join(proprias)
    return f"{proprias} -c timezone=UTC".strip()


def run_migrations_online() -> None:
    """Connects to the database and applies migrations."""
    url, connect_args = _connect_args(_get_sync_url())
    connect_args["options"] = _session_options(url)

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # One transaction PER migration, not one for the whole batch. Without this,
            # the `autocommit_block()` of 20260829_0001 (needed for CREATE
            # INDEX CONCURRENTLY) commits, as a side effect, ALL the
            # migrations that ran before it in the same `upgrade head` — if the
            # indexes fail, the database is left in a partial state that
            # alembic_version does not describe. It is what alembic's own
            # documentation recommends for those using autocommit_block.
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
