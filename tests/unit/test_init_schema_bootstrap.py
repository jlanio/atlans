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
SQL_DO_NUCLEO = (RAIZ / "scripts" / "init_schema.sql").read_text(encoding="utf-8")
SQL_DAS_EXTENSOES = [p.read_text(encoding="utf-8") for p in esquemas()]
SQL = "\n".join([SQL_DO_NUCLEO, *SQL_DAS_EXTENSOES])

# `alembic_version` is created by the script but is not a model.
_SO_DO_SCRIPT = {"alembic_version"}

_CRIADAS = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", SQL))
_DROPADAS = set(re.findall(r"DROP TABLE IF EXISTS (\w+) CASCADE", SQL))
_TABELAS_DOS_MODELS = set(Base.metadata.tables)

# Words that open a constraint, not a column, inside the CREATE TABLE.
_NAO_E_COLUNA = {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "EXCLUDE", "LIKE"}


def _colunas_do_script() -> dict:
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
            if not re.fullmatch(r"\w+", token or "") or token.upper() in _NAO_E_COLUNA:
                continue
            colunas.add(token.lower())
        fora[nome] = colunas
    return fora


_COLUNAS_DO_SCRIPT = _colunas_do_script()


def test_todo_model_tem_create_no_script():
    assert not (_TABELAS_DOS_MODELS - _CRIADAS)


def test_toda_tabela_criada_tem_o_drop_correspondente():
    assert not (_CRIADAS - _DROPADAS)


def test_o_script_nao_cria_tabela_que_nao_e_de_nenhum_model():
    assert not (_CRIADAS - _TABELAS_DOS_MODELS - _SO_DO_SCRIPT)


def _criadas(sql: str) -> set[str]:
    return set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", sql))


# The tables of the models that live in an extension.
_TABELAS_DE_EXTENSAO = {
    m.local_table.name for m in Base.registry.mappers
    if m.class_.__module__.startswith("app.extensoes.")
}


def test_tabela_de_extensao_nao_mora_no_script_do_nucleo():
    """Without the extension (the free distribution), one of its tables in the core
    script would be a table with no model, created on every installation. It lives
    in the extension's `schema.sql`, with the DROP alongside."""
    assert not (_criadas(SQL_DO_NUCLEO) & _TABELAS_DE_EXTENSAO)
    das_extensoes = set().union(set(), *(_criadas(sql) for sql in SQL_DAS_EXTENSOES))
    assert _TABELAS_DE_EXTENSAO <= das_extensoes


@pytest.mark.parametrize(
    "tabela",
    ["user_executor_assignments", "audit_events", "executor_enrollment_otp"],
)
def test_tabelas_que_ja_faltaram(tabela):
    """Named regressions: the three that have already broken a bootstrap."""
    assert tabela in _CRIADAS and tabela in _DROPADAS


def test_toda_coluna_de_model_existe_no_script():
    """The hole the TABLE NAME test could not see: a new column in the model and
    in the migration, but forgotten in the script — a new database is born without it, forever."""
    faltando = {}
    for tabela, obj in Base.metadata.tables.items():
        no_script = _COLUNAS_DO_SCRIPT.get(tabela)
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
def test_colunas_que_o_teste_por_nome_deixava_passar(tabela, coluna):
    """Named COLUMN regressions — the analogue of the table test above."""
    assert coluna in _COLUNAS_DO_SCRIPT[tabela]


def test_nenhum_indice_aponta_para_tabela_inexistente():
    """`ix_otp_unused` was created on `agent_enrollment_otp`, the name before the
    20260716_0001 rename — the whole script blew up in section 2."""
    alvos = set(re.findall(r"CREATE (?:UNIQUE )?INDEX \w+ ON (\w+)", SQL))
    assert not (alvos - _CRIADAS)


def test_carimbo_do_alembic_e_a_head_real():
    """A stamp later than the script's content is exactly the bug it has already
    had: alembic considers applied what never ran."""
    carimbo = re.search(r"INSERT INTO alembic_version \(version_num\) VALUES \('(\w+)'\)", SQL)
    assert carimbo

    versoes = RAIZ / "alembic" / "versions"
    revisoes, down = set(), set()
    for arquivo in versoes.glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        # The type annotation varies between migrations (`: str`, `: Union[str, None]`,
        # none); matching only `: str` left almost every `down_revision` out,
        # and "heads" became the set of ALL revisions — any old stamp
        # passed.
        for m in re.finditer(r'^revision(?::[^=\n]+)?\s*=\s*"(\w+)"', texto, re.M):
            revisoes.add(m.group(1))
        for m in re.finditer(r'^down_revision(?::[^=\n]+)?\s*=\s*"(\w+)"', texto, re.M):
            down.add(m.group(1))

    heads = revisoes - down
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
