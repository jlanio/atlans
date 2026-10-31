# app/models/__init__.py
"""Every model module of the package, so `Base.metadata` is complete.

alembic/env.py imports this package to build the metadata that
`alembic revision --autogenerate` compares with the database. With a
hand-written list here (and another in env.py), a forgotten module meant its
tables were missing from that metadata, and autogenerate proposed DROP TABLE
for them — eight tables were in that state (audit_events, portal_layers,
usage_daily, ...). Walking the package picks up a new model file on its own.
"""
import importlib
import pkgutil

for _modulo in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_modulo.name}")

# The tables of the extensions present (app/extensoes), after the core ones.
from app.extensoes import importar_modelos  # noqa: E402

importar_modelos()
