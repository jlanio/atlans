"""
Alembic env.py — configuração de ambiente para migrações do Atlas Studio.

Suporta dois modos:
  - offline: gera SQL sem conectar ao banco
  - online:  conecta ao banco e aplica migrações diretamente

A DATABASE_URL é lida da variável de ambiente (ou .env via python-dotenv).
O driver asyncpg é trocado por psycopg2 para compatibilidade com Alembic (síncrono).
"""
import os
import re
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Garante que o root do projeto está no sys.path para importar app.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

load_dotenv()

# Importa Base e todos os models para que metadata esteja populado
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


# Tabelas de sistema do PostGIS — não devem ser gerenciadas pelo Alembic
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
    """Filtra objetos que o Alembic não deve gerenciar."""
    if type_ == "table" and name in _POSTGIS_TABLES:
        return False
    return True


def _get_sync_url() -> str:
    """
    Retorna DATABASE_URL convertida para driver síncrono (psycopg2).
    Remove sslmode da query string e repassa via connect_args se necessário.
    """
    url = os.environ["DATABASE_URL"]
    # Troca driver async por sync
    url = url.replace("+asyncpg", "+psycopg2").replace("postgresql://", "postgresql+psycopg2://")
    # Remove prefixo asyncpg sem dialeto explícito
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
    return url


def run_migrations_offline() -> None:
    """Gera SQL de migração sem conectar ao banco (útil para revisão/CI)."""
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
    """Conecta ao banco e aplica migrações."""
    url = _get_sync_url()

    # Extrai ssl/sslmode da URL e passa via connect_args para psycopg2
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
            # Uma transacao POR migration, nao uma para o lote inteiro. Sem isto,
            # o `autocommit_block()` de 20260829_0001 (necessario para o CREATE
            # INDEX CONCURRENTLY) commita como efeito colateral TODAS as
            # migrations que rodaram antes dela no mesmo `upgrade head` — se os
            # indices falharem, o banco fica num estado parcial que o
            # alembic_version nao descreve. E a recomendacao da propria
            # documentacao do alembic para quem usa autocommit_block.
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
