"""Base zero: the database is born ready.

Collapses the chain of 53 migrations into a single initial revision (F3 of the
simplification — docs/specs/simplification.md, A9/N3; premise given by the owner:
nothing is really in production, there is no legacy database to preserve).

The body does NOT live here: it is `scripts/init_schema.sql` itself, read and
executed on the spot. It is the same file the convergence tests already pin to the
models (tests/unit/test_init_schema_bootstrap.py), so alembic, psql and tests
see ONE source of truth — the divergence between "what the chain builds"
and "what the script builds", which the convergence test guarded, can no longer
exist. After it comes the `schema.sql` of each extension present
(`app/extensoes`, see `esquemas()`): the tables that only exist with it.

Before executing, the filter strips from the script only the commands on
`alembic_version` (DROP/CREATE/INSERT): inside alembic, that table is managed
by alembic itself; the file's INSERT exists for the psql path and here it
would become a duplicate row. The DROPs of the application tables STAY — on an
empty database they are no-ops, and they keep the text identical to the manual reset.

EXISTING database (stamped at a revision of the old chain): the schema does not
change — the squash produces the same DDL the chain produced. Run once:

    alembic stamp --purge 9ed006ca1660

or reset from scratch with `psql -f scripts/init_schema.sql` (the script itself
stamps this revision).
"""
import re
from pathlib import Path

import sqlalchemy as sa
from alembic import context, op

revision = "9ed006ca1660"  # pragma: allowlist secret
down_revision = None
branch_labels = None
depends_on = None

_RAIZ = Path(__file__).resolve().parents[2]


def _sql_sem_alembic_version(sql: str) -> str:
    """The script ready for `op.execute`.

    Two cuts, neither of them changing the effect on an empty database:
    - the commands on `alembic_version` (reason in the module docstring);
    - the lines that are ONLY comments: `op.execute` passes the text through
      `sqlalchemy.text()`, which reads `:palavra` (any `:word`) as a bind — and the commented-out
      GRANTs section uses `:app_user` as a psql variable. Without this cut, the
      upgrade fails asking for a value for a parameter that only exists in a
      comment. On the psql path the file stays intact, comments and all.
    """
    sql = re.sub(r"^DROP TABLE IF EXISTS alembic_version CASCADE;[^\n]*$", "", sql, flags=re.M)
    sql = re.sub(r"^CREATE TABLE alembic_version \(.*?\);[^\n]*$", "", sql, flags=re.M | re.S)
    sql = re.sub(r"^INSERT INTO alembic_version[^\n]*$", "", sql, flags=re.M)
    sql = re.sub(r"^\s*--[^\n]*$", "", sql, flags=re.M)
    # No executable command targeting the alembic table may remain, and
    # no fake psql bind may reach text().
    sobras = re.search(r"^\s*(DROP|CREATE|INSERT)[^\n]*alembic_version", sql, flags=re.M | re.I)
    assert not sobras, f"filtro deixou passar: {sobras.group(0)!r}"
    assert ":app_user" not in sql
    return sql


# The preamble of the offline script (--sql): reproduces the online mode's guard
# on the side of whoever EXECUTES it. `alembic_version` may not exist yet at the
# point the preamble runs (alembic creating it depends on the mode), hence
# the dynamic EXECUTE: present and stamped -> proceed; present and empty, or
# absent, with application tables in the database -> abort before the DROP ALL.
_GUARDA_OFFLINE = """
DO $guarda_base_zero$
DECLARE
    carimbos bigint;
BEGIN
    IF to_regclass('public.users') IS NULL THEN
        RETURN; -- banco vazio: o caminho legítimo
    END IF;
    IF to_regclass('public.alembic_version') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM alembic_version' INTO carimbos;
        IF carimbos > 0 THEN
            RETURN; -- carimbado: o alembic online nem teria chegado aqui
        END IF;
    END IF;
    RAISE EXCEPTION 'base zero: este banco tem tabelas da aplicacao e nenhum carimbo — o corpo e DROP ALL + CREATE ALL. Cadeia antiga? alembic stamp --purge 9ed006ca1660. Reset intencional? psql -f scripts/init_schema.sql.';
END
$guarda_base_zero$;
"""


def upgrade() -> None:
    # Guard for the only destructive path base zero would open: a database WITH
    # application tables and WITHOUT a stamp (alembic_version empty or absent).
    # Only in that state does alembic decide "nothing applied" and get here — and the
    # body is DROP ALL + CREATE ALL. A database from the old chain never gets here (the
    # unknown stamp brings alembic down first, without touching anything); an empty
    # database passes.
    #
    # In offline mode (--sql) there is no database to inspect AT GENERATION — but the
    # generated script is executable and runs out of alembic's sight. So the
    # SAME guard goes in as the script's own preamble (a DO that aborts on a
    # populated database without a stamp), instead of trusting that nobody applies it
    # blindly. Generating always keeps working; it is the EXECUTION that refuses.
    if context.is_offline_mode():
        op.execute(_GUARDA_OFFLINE)
    else:
        tem_users = op.get_bind().execute(
            sa.text("SELECT to_regclass('public.users') IS NOT NULL")
        ).scalar()
        if tem_users:
            raise RuntimeError(
                "Este banco ja tem tabelas da aplicacao, mas nenhum carimbo do "
                "alembic — executar a base zero aqui APAGARIA os dados (o corpo "
                "dela e DROP ALL + CREATE ALL). Se e um banco da cadeia antiga: "
                "alembic stamp --purge 9ed006ca1660. Se o reset e intencional: "
                "psql -f scripts/init_schema.sql."
            )

    caminho = _RAIZ / "scripts" / "init_schema.sql"
    op.execute(_sql_sem_alembic_version(caminho.read_text(encoding="utf-8")))

    # The tables of each extension present, after the core ones and with the same
    # filter. Without extensions (the free distribution), nothing.
    from app.extensoes import esquemas

    for esquema in esquemas():
        op.execute(_sql_sem_alembic_version(esquema.read_text(encoding="utf-8")))


def downgrade() -> None:
    raise RuntimeError(
        "A base zero nao tem downgrade: abaixo dela nao existe estado. "
        "Para descartar o banco, rode scripts/init_schema.sql (DROP ALL + CREATE ALL)."
    )
