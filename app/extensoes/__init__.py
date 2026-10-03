# app/extensoes/__init__.py
"""
Extensions: what an installation can have beyond the core.

Each subpackage of `app/extensoes/` is an extension — the paid plans, in the
installation that sells subscriptions, are one. The core NEVER imports an
extension by name: on the first call to `registro()`, each subpackage is
imported and its `registrar(registro)` function hangs on the `Registro` what
the extension brings. With no extension at all — the free distribution —, each
plug-in point has a default in the core, and nothing is missing.

  rotas              APIRouters included after the core's
  tarefas_de_fundo   (name, factory) added to the lifespan's (`app/main.py`)
  plano_e_teto       a person's plan and assistant token ceiling
                     (default: no plan, and the ceiling from `app/mcp/cotas.py`)
  assinaturas_ativas whether the screen offers subscribing to a plan (default: no)
  templates          email template folders, consulted after the core's
  painel_do_modelo   extra fields in the admin panel for the assistant's model

An extension's SQLAlchemy models live in `<extensão>/modelos`, and enter
`Base.metadata` through `importar_modelos()` (called in `app/models/__init__.py`).
Their tables, in `<extensão>/schema.sql` (DROP + CREATE, like the core's
`scripts/init_schema.sql`): the alembic zero base runs each one, after the
core's script (`esquemas()`).

ATLANS_SEM_EXTENSOES=1 ignores the extensions present: that is how the tests
prove the core runs on its own. An extension that is present but fails to
import brings startup down — silently vanishing along with billing would be
worse.

Only the standard library here: `app/models/__init__.py` imports this module.
"""
from __future__ import annotations

import importlib
import os
import pkgutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# A person's (plan | None, ceiling). Receives `user_id` and, by name, `db` and `redis`.
PlanoETeto = Callable[..., Awaitable[tuple[str | None, int]]]
# Extra fields in the model panel. Receives `db` and, by name, `atual`, `catalogo`,
# `simular` and `consulta` (the URL parameters); returns what to add to the panel.
ContribuicaoAoPainel = Callable[..., Awaitable[dict[str, Any]]]
TarefaDeFundo = tuple[str, Callable[[], Awaitable[object]]]


def _nenhuma() -> bool:
    return False


@dataclass
class Registro:
    nomes: list[str] = field(default_factory=list)
    rotas: list[Any] = field(default_factory=list)
    tarefas_de_fundo: list[TarefaDeFundo] = field(default_factory=list)
    plano_e_teto: PlanoETeto | None = None
    # A function, not a boolean: the value depends on the extension's
    # configuration, read when the screen asks.
    assinaturas_ativas: Callable[[], bool] = field(default=_nenhuma)
    templates: list[Path] = field(default_factory=list)
    painel_do_modelo: list[ContribuicaoAoPainel] = field(default_factory=list)


_registro: Registro | None = None


def desligadas() -> bool:
    """ATLANS_SEM_EXTENSOES: the core alone, even with extensions on disk."""
    return os.getenv("ATLANS_SEM_EXTENSOES", "").strip().lower() in ("1", "true", "sim", "yes", "on")


def _nomes() -> list[str]:
    if desligadas():
        return []
    return sorted(
        m.name for m in pkgutil.iter_modules(__path__)
        if m.ispkg and not m.name.startswith("_")
    )


def registro() -> Registro:
    """The registry of the extensions present, assembled on the first call."""
    global _registro
    if _registro is None:
        novo = Registro()
        for nome in _nomes():
            modulo = importlib.import_module(f"{__name__}.{nome}")
            registrar = getattr(modulo, "registrar", None)
            if registrar is None:
                raise RuntimeError(f"A extensão {nome!r} não tem registrar(registro).")
            registrar(novo)
            novo.nomes.append(nome)
        _registro = novo
    return _registro


def importar_modelos() -> None:
    """Imports `<extensão>/modelos` from each extension that has it."""
    for nome in _nomes():
        alvo = f"{__name__}.{nome}.modelos"
        try:
            importlib.import_module(alvo)
        except ModuleNotFoundError as exc:
            # Only the absence of its OWN `modelos` is normal (an extension without tables).
            if exc.name != alvo:
                raise


def esquemas() -> list[Path]:
    """The `schema.sql` of each present extension that has tables, in name order.

    Without importing the extension: the alembic zero base runs this, and what
    it needs is the file, not the code.
    """
    achados = []
    for nome in _nomes():
        for raiz in __path__:
            alvo = Path(raiz) / nome / "schema.sql"
            if alvo.is_file():
                achados.append(alvo)
                break
    return achados
