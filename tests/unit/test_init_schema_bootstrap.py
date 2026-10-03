# tests/unit/test_init_schema_bootstrap.py
"""`scripts/init_schema.sql` has to be a real "DROP ALL + CREATE ALL".

The script stamps `alembic_version` at head, so `alembic upgrade head` never
again runs anything on a database created by it: whatever is missing here stays
missing forever, with no possible fix via alembic. That is how
`user_executor_assignments` disappeared (500 on the first executor assignment) and
how `audit_events` was born without a table.

The reverse also breaks: a table in the CREATE but outside the DROP block makes
the reset of an existing database abort halfway (with ON_ERROR_STOP, after
everything has already been dropped) or silently keep the old data.

An extension's tables (`app/extensoes`) live in its own `schema.sql`, which the
from-scratch setup runs after the core script: the database is the sum of the two,
and it is the sum that is compared with the models. Without the extension, neither
its model nor its SQL is here, and the core has to be consistent on its own.
"""
import importlib
import pkgutil
import re
from pathlib import Path

import pytest

import app.models
from app.extensoes import esquemas
from app.models.base import Base

# `app.models.__init__` imports only some of the modules; to compare with the
# script the metadata must be COMPLETE — otherwise the test passes precisely when
# a new model was forgotten, which is the case it exists to catch.
for _mod in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{_mod.name}")

RAIZ = Path(__file__).resolve().parents[2]
CORE_SQL = (RAIZ / "scripts" / "init_schema.sql").read_text(encoding="utf-8")
EXTENSIONS_SQL = [p.read_text(encoding="utf-8") for p in esquemas()]
SQL = "\n".join([CORE_SQL, *EXTENSIONS_SQL])

# `alembic_version` is created by the script but is not a model.
_SO_DO_SCRIPT = {"alembic_version"}

_CREATED = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", SQL))
_DROPADAS = set(re.findall(r"DROP TABLE IF EXISTS (\w+) CASCADE", SQL))
_MODEL_TABLES = set(Base.metadata.tables)

# Words that open a constraint, not a column, inside the CREATE TABLE.
_NOT_A_COLUMN = {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "EXCLUDE", "LIKE"}


def _script_columns() -> dict:
    """Columns declared in each `CREATE TABLE` of the script.

    Comparing only TABLE NAMES lets through the most common case of divergence
    between the three bootstrap paths: a new COLUMN. `workflows.origem`
    came in through a migration and the model; had it been left out of the script,
    a database created by it would be born without the column — and, since the
    script already stamps the alembic head, no later `upgrade` would create it.
    """
    blocos = re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)\s*\((.*?)\n\);", SQL, re.S)
    fora = {}
    for nome, corpo in blocos:
        colunas = set()
        for linha in corpo.splitlines():
            linha = re.sub(r"--.*$", "", linha).strip()
            if not linha:
                continue
            token = linha.split()[0].strip('",').strip('"')
            if not re.fullmatch(r"\w+", token or "") or token.upper() in _NOT_A_COLUMN:
                continue
            colunas.add(token.lower())
        fora[nome] = colunas
    return fora


_SCRIPT_COLUMNS = _script_columns()


def test_every_model_has_create_in_script():
    assert not (_MODEL_TABLES - _CREATED)


def test_every_created_table_has_matching_drop():
    assert not (_CREATED - _DROPADAS)


def test_script_does_not_create_table_without_a_model():
    assert not (_CREATED - _MODEL_TABLES - _SO_DO_SCRIPT)


def _created_tables(sql: str) -> set[str]:
    return set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", sql))


# The tables of the models that live in an extension.
_EXTENSION_TABLES = {
    m.local_table.name for m in Base.registry.mappers
    if m.class_.__module__.startswith("app.extensoes.")
}


def test_extension_table_does_not_live_in_core_script():
    """Without the extension (the free distribution), one of its tables in the core
    script would be a table with no model, created on every installation. It lives
    in the extension's `schema.sql`, with the DROP alongside."""
    assert not (_created_tables(CORE_SQL) & _EXTENSION_TABLES)
    from_extensions = set().union(set(), *(_created_tables(sql) for sql in EXTENSIONS_SQL))
    assert _EXTENSION_TABLES <= from_extensions


@pytest.mark.parametrize(
    "tabela",
    ["user_executor_assignments", "audit_events", "executor_enrollment_otp"],
)
def test_tables_that_were_missing_before(tabela):
    """Named regressions: the three that have already broken a bootstrap."""
    assert tabela in _CREATED and tabela in _DROPADAS


def test_every_model_column_exists_in_script():
    """The hole the TABLE NAME test could not see: a new column in the model and
    in the migration, but forgotten in the script — a new database is born without it, forever."""
    faltando = {}
    for tabela, obj in Base.metadata.tables.items():
        no_script = _SCRIPT_COLUMNS.get(tabela)
        if no_script is None:
            continue  # absence of the TABLE is already covered by another test
        ausentes = {c.name.lower() for c in obj.columns} - no_script
        if ausentes:
            faltando[tabela] = sorted(ausentes)
    assert not faltando, f"colunas no model e fora do init_schema.sql: {faltando}"


@pytest.mark.parametrize(
    ("tabela", "coluna"),
    [("workflows", "origem"), ("users", "agent_quota"), ("workflow_runs", "trigger_source")],
)
def test_columns_the_name_based_test_let_through(tabela, coluna):
    """Named COLUMN regressions — the analogue of the table test above."""
    assert coluna in _SCRIPT_COLUMNS[tabela]


def test_no_index_points_to_missing_table():
    """`ix_otp_unused` was created on `agent_enrollment_otp`, the name before the
    20260716_0001 rename — the whole script blew up in section 2."""
    alvos = set(re.findall(r"CREATE (?:UNIQUE )?INDEX \w+ ON (\w+)", SQL))
    assert not (alvos - _CREATED)


def test_carimbo_do_alembic_e_a_head_real():
    """A stamp later than the script's content is exactly the bug it has already
    had: alembic considers applied what never ran."""
    carimbo = re.search(r"INSERT INTO alembic_version \(version_num\) VALUES \('(\w+)'\)", SQL)
    assert carimbo

    versoes = RAIZ / "alembic" / "versions"
    revisions, down = set(), set()
    for arquivo in versoes.glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        # The type annotation varies between migrations (`: str`, `: Union[str, None]`,
        # none); matching only `: str` left almost every `down_revision` out,
        # and "heads" became the set of ALL revisions — any old stamp
        # passed.
        for m in re.finditer(r'^revision(?::[^=\n]+)?\s*=\s*"(\w+)"', texto, re.M):
            revisions.add(m.group(1))
        for m in re.finditer(r'^down_revision(?::[^=\n]+)?\s*=\s*"(\w+)"', texto, re.M):
            down.add(m.group(1))

    heads = revisions - down
    assert len(heads) == 1, f"a cadeia de migracoes tem mais de uma head: {sorted(heads)}"
    assert carimbo.group(1) in heads


def test_system_config_updated_at_e_not_null():
    """The squash lost the NOT NULL that the old chain created — and the model requires it.

    `docs`/the migration itself promise "the same DDL the chain produced"; a
    new database was born with `system_config.updated_at` nullable while the model
    declares `nullable=False`. Regression from the 2026-09-24 adversarial review —
    pinned here column by column until full NULLABILITY convergence holds.
    """
    import re as _re

    bloco = _re.search(r"CREATE TABLE system_config \((.*?)\);", SQL, _re.S)
    assert bloco, "CREATE TABLE system_config sumiu do init_schema.sql"
    assert _re.search(r"updated_at\s+TIMESTAMP\s+DEFAULT\s+now\(\)\s+NOT\s+NULL", bloco.group(1)), (
        "system_config.updated_at precisa de NOT NULL (o model tem nullable=False)"
    )
