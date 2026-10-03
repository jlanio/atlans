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
from alembic import context
from dotenv import load_dotenv

# Ensure the project root is on sys.path so app.* can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

load_dotenv()

# Import Base and all models so the metadata is populated
from app.models.base import Base  # noqa: E402
from app.models import (  # noqa: F401, E402
    models,
    user,
    workspace,
    credential,
    system_config,
    workspace_member,
    artifact,
    executor,
    workspace_executor,
    api_token,
    conversa,
)

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
    Removes sslmode from the query string and passes it via connect_args if needed.
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


def run_migrations_online() -> None:
    """Connects to the database and applies migrations."""
    url = _get_sync_url()

    # Extract ssl/sslmode from the URL and pass it via connect_args to psycopg2
    sslmode = None
    match = re.search(r"[?&](?:ssl|sslmode)=([^&]+)", url)
    if match:
        raw_value = match.group(1).lower()
        sslmode = "disable" if raw_value in {"disable", "false", "0", "no", "allow"} else "require"
        url = re.sub(r"[?&](?:ssl|sslmode)=[^&]*", "", url)
        url = re.sub(r"\?&", "?", url)
        url = url.rstrip("?&")

    connect_args = {}
    if sslmode:
        connect_args["sslmode"] = sslmode

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
