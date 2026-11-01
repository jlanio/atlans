# tests/unit/test_metadata_do_alembic.py
"""The metadata alembic compares with the database has EVERY model table.

alembic/env.py imported a hand-written list of model modules, and eight tables
(audit_events, executor_enrollment_otp, node_run_metrics, portal_features,
portal_layers, usage_daily, user_executor_assignments, workflow_run_metrics)
were missing from it: `alembic revision --autogenerate` proposed DROP TABLE for
each one. Now env.py imports the `app.models` package, which walks its own
modules.

The check runs env.py itself in a FRESH interpreter: `Base.metadata` is global
to the process, and in the suite some other test has always imported every
model already — in-process, the test would pass with the list still short.
The expected set comes from the model files' source (`__tablename__`), not
from importing them, for the same reason.
"""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ENV_PY = RAIZ / "alembic" / "env.py"

# Loads env.py by path with a stand-in for `alembic.context` in offline mode:
# nothing connects, `context.configure` and `run_migrations` do nothing, and
# the module's `target_metadata` is what a real run would compare.
_CARREGAR_ENV = r"""
import contextlib, importlib.util, json, sys, types
import alembic

class _Config:
    config_file_name = None
    config_ini_section = "alembic"
    def get_section(self, *_a, **_k):
        return {}

contexto = types.ModuleType("alembic.context")
contexto.config = _Config()
contexto.is_offline_mode = lambda: True
contexto.configure = lambda **_k: None
contexto.begin_transaction = contextlib.nullcontext
contexto.run_migrations = lambda: None
alembic.context = contexto
sys.modules["alembic.context"] = contexto

spec = importlib.util.spec_from_file_location("alembic_env", sys.argv[1])
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
print(json.dumps(sorted(env.target_metadata.tables)))
"""


def _tables_in_the_sources() -> set[str]:
    """`__tablename__ = "..."` of every class in the model packages."""
    arquivos = list((RAIZ / "app" / "models").glob("*.py"))
    # An extension's models live in app/extensoes/<extensão>/modelos.
    arquivos += list((RAIZ / "app" / "extensoes").glob("*/modelos/*.py"))
    arquivos += list((RAIZ / "app" / "extensoes").glob("*/modelos.py"))
    nomes = set()
    for arquivo in arquivos:
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            if (
                isinstance(no, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in no.targets)
                and isinstance(no.value, ast.Constant)
            ):
                nomes.add(no.value.value)
    return nomes


def _tables_alembic_sees() -> set[str]:
    ambiente = {
        **os.environ,
        "PYTHONPATH": str(RAIZ),
        # Offline mode only builds the URL; nothing connects.
        "DATABASE_URL": "postgresql+asyncpg://u:p@127.0.0.1:1/x",  # pragma: allowlist secret
    }
    saida = subprocess.run(
        [sys.executable, "-c", _CARREGAR_ENV, str(ENV_PY)],
        cwd=RAIZ, env=ambiente, capture_output=True, text=True, timeout=120,
    )
    assert saida.returncode == 0, saida.stderr[-3000:]
    return set(json.loads(saida.stdout.strip().splitlines()[-1]))


def test_alembic_sees_every_model_table():
    esperadas = _tables_in_the_sources()
    # Sanity check of the source reading itself: some of the tables that were missing.
    assert {"audit_events", "usage_daily", "portal_layers", "users"} <= esperadas
    vistas = _tables_alembic_sees()
    assert esperadas - vistas == set(), "tabelas fora do metadata do alembic (autogenerate as apagaria)"
    assert vistas - esperadas == set()
