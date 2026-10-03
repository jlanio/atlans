# tests/unit/test_base_zero.py
"""The zero baseline (F3 of the simplification): one revision, whose body is init_schema.

What dies if any of these fails:

- More than one file in `alembic/versions/` means the chain started growing
  ON TOP of the zero baseline again without a decision — the new path is to edit
  `init_schema.sql` (the body) while nothing is in production, or to reopen the
  incremental-migrations discussion when something is.
- The `alembic_version` filter letting a command through makes the upgrade
  duplicate the stamp (the file's INSERT + alembic's own).
- The script's stamp diverging from `revision` makes psql and alembic produce
  databases that disagree about their own version.

CONTENT convergence (tables/columns × models) stays with
`test_init_schema_bootstrap.py` — here it is the mechanics of the single revision.
"""
import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[2]
VERSOES = RAIZ / "alembic" / "versions"
SQL = (RAIZ / "scripts" / "init_schema.sql").read_text(encoding="utf-8")


def _base_zero():
    """Imports the migration by path — `alembic/` is not a package."""
    (arquivo,) = [p for p in VERSOES.glob("*.py") if p.name != "__init__.py"]
    spec = importlib.util.spec_from_file_location("base_zero", arquivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ha_exatamente_uma_revisao():
    arquivos = [p.name for p in VERSOES.glob("*.py") if p.name != "__init__.py"]
    assert len(arquivos) == 1, f"a cadeia voltou a crescer: {sorted(arquivos)}"


def test_a_revisao_e_inicial():
    mod = _base_zero()
    assert mod.down_revision is None


def test_o_filtro_tira_todo_comando_sobre_alembic_version():
    mod = _base_zero()
    filtrado = mod._sql_sem_alembic_version(SQL)
    assert not re.search(
        r"^\s*(DROP|CREATE|INSERT)[^\n]*alembic_version", filtrado, re.M | re.I
    )
    # And only that: the rest of the script is there whole.
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in filtrado
    assert "CREATE TABLE users" in filtrado
    assert "DROP TABLE IF EXISTS users CASCADE" in filtrado


def test_o_filtro_nao_engole_o_script_num_regex_guloso():
    """The `CREATE TABLE alembic_version (...)` is removed with re.S; a greedy
    regex would eat from there to the LAST `);` of the file. The neighboring
    tables (audit_events before, the INSERT after) have to survive.

    The count anchors at line start because comments also say
    "CREATE TABLE" — and the filter removes comments on purpose."""
    mod = _base_zero()
    filtrado = mod._sql_sem_alembic_version(SQL)
    assert "CREATE TABLE audit_events" in filtrado

    def comandos(texto):
        return len(re.findall(r"^CREATE TABLE ", texto, re.M))

    assert comandos(filtrado) == comandos(SQL) - 1


def test_o_carimbo_do_script_e_a_propria_revisao():
    carimbo = re.search(
        r"INSERT INTO alembic_version \(version_num\) VALUES \('(\w+)'\)", SQL
    )
    assert carimbo
    assert carimbo.group(1) == _base_zero().revision


def test_upgrade_recusa_banco_populado_sem_carimbo():
    """The only destructive path: tables present + empty alembic_version is
    the only state in which alembic reaches the zero baseline's body with data in
    the way — and the body is DROP ALL. The guard has to exist, query the database
    (to_regclass) and point to the two remedies. Proven live in the F3
    delivery; here the text pins the guard against accidental removal."""
    (arquivo,) = [p for p in VERSOES.glob("*.py") if p.name != "__init__.py"]
    fonte = arquivo.read_text(encoding="utf-8")
    assert "to_regclass('public.users')" in fonte
    assert "APAGARIA" in fonte
    assert "stamp --purge 9ed006ca1660" in fonte
    # And the guard must not block offline generation (--sql).
    assert "is_offline_mode" in fonte


def test_upgrade_roda_o_schema_de_cada_extensao_depois_do_nucleo(monkeypatch, tmp_path):
    """An extension's tables (app/extensoes) live in its `schema.sql`: the
    zero baseline runs the core script and, after it, each one — with the same filter.
    Without extensions, only the core one."""
    import app.extensoes

    esquema = tmp_path / "schema.sql"
    esquema.write_text("-- so comentario\nCREATE TABLE de_extensao (id INT);\n", encoding="utf-8")
    mod = _base_zero()
    executados: list[str] = []
    banco_vazio = SimpleNamespace(execute=lambda *_a, **_k: SimpleNamespace(scalar=lambda: False))
    monkeypatch.setattr(mod, "op", SimpleNamespace(execute=executados.append, get_bind=lambda: banco_vazio))
    monkeypatch.setattr(mod, "context", SimpleNamespace(is_offline_mode=lambda: False))

    monkeypatch.setattr(app.extensoes, "esquemas", lambda: [esquema])
    mod.upgrade()
    assert len(executados) == 2
    assert "CREATE TABLE users" in executados[0]
    assert executados[1].strip() == "CREATE TABLE de_extensao (id INT);"

    executados.clear()
    monkeypatch.setattr(app.extensoes, "esquemas", lambda: [])
    mod.upgrade()
    assert len(executados) == 1


def test_downgrade_recusa_com_o_caminho_certo():
    with pytest.raises(RuntimeError, match="init_schema"):
        _base_zero().downgrade()


def test_nenhum_resto_de_atlans_drop():
    """The ATLANS_DROP_* flags were the opt-in for destructive downgrade in the
    old migrations; they died with them. A leftover executable mention is
    dead code path coming back."""
    for arquivo in VERSOES.glob("*.py"):
        assert "ATLANS_DROP" not in arquivo.read_text(encoding="utf-8")


def test_guarda_tambem_no_offline():
    """The --sql output is an EXECUTABLE script — and it runs far from alembic's eyes.

    The online guard (to_regclass) doesn't exist in offline generation; without
    the preamble, the generated script applied blindly to a populated database
    without a stamp did the DROP ALL without a single question (finding from the
    adversarial review of 2026-09-24). Generating is still always allowed; it is
    the EXECUTION that refuses.
    """
    mod = _base_zero()
    assert "DO $guarda_base_zero$" in mod._GUARDA_OFFLINE
    assert "RAISE EXCEPTION" in mod._GUARDA_OFFLINE
    fonte = (VERSOES / [p.name for p in VERSOES.glob("*.py") if p.name != "__init__.py"][0]).read_text(
        encoding="utf-8"
    )
    assert re.search(r"if context\.is_offline_mode\(\):\s*\n\s*op\.execute\(_GUARDA_OFFLINE\)", fonte), (
        "o modo offline precisa emitir a guarda como preâmbulo do script"
    )


def test_dockerfile_leva_o_corpo_da_migracao():
    """The migration reads scripts/init_schema.sql AT RUNTIME (`_RAIZ / "scripts"`).

    Without the copy in Dockerfile.api the body is left OUT of the image: any
    `alembic upgrade head` in production — a new database, or a deploy that
    applies the migrations on its own to an empty database — dies with
    FileNotFoundError before creating the schema. In stamped production nobody
    notices, because the upgrade never runs (finding from the adversarial review
    of 2026-09-24).
    """
    dockerfile = (RAIZ / "Dockerfile.api").read_text(encoding="utf-8")
    assert re.search(
        r"(?m)^COPY\s+scripts/init_schema\.sql\s+\./scripts/init_schema\.sql\s*$", dockerfile
    ), "Dockerfile.api precisa copiar scripts/init_schema.sql — o corpo da base zero é lido em runtime"
