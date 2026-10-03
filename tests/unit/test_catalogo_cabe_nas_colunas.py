# tests/unit/test_catalogo_cabe_nas_colunas.py
"""The versioned catalog fits in the database columns — checked in CI.

**This is the test that was missing, and the reason it was missing is instructive.**
The rest of the suite runs on SQLite, and SQLite **ignores the declared size of
`VARCHAR`**: `VARCHAR(255)` accepts 10 thousand characters without complaining.
PostgreSQL doesn't. So the overflow that brought down the import in production
was, by construction, invisible to every import test there is — they passed with
the same data Postgres rejected.

What happened: 48 of the 25,492 records in `catalogo/geoservicos` had a `titulo`
over 255 characters (the longest, an IBGE indicator, with 276). Since
`importar_pasta` commits 500 at a time, the batch containing the first of them
(position 6,779) raised `StringDataRightTruncationError` and aborted the rest:
6,500 records in the database, 18,992 lost, and nothing but an ERROR in the log.
The assistant was left without three quarters of the layers it should know how
to find.

This test doubles nothing and doesn't touch a database: it reads the repository's
REAL catalog and compares each field with the COLUMN's limit, taken from the
model. It fails in CI on the day someone adds to the catalog a record Postgres
would reject — which is exactly the day you want to know.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.models.fonte_de_dados import FonteDeDados
from app.services import fontes_service as fs
from app.services import fontes_vault

CATALOGO = Path(__file__).resolve().parents[2] / "catalogo" / "geoservicos"

# Everything the Vault fills in. Which of them the database LIMITS is a question
# for the model, not for this list: writing "titulo is out because it became TEXT"
# here would make the test stop seeing precisely the field that caused the
# overflow, on the day someone reverted the column.
DO_VAULT = ("instituicao", "grupo", "titulo", "type_name", "url")


def _registros():
    if not CATALOGO.is_dir():
        pytest.skip(f"catálogo não está neste checkout ({CATALOGO})")
    return [r for r in fontes_vault.ler_pasta(CATALOGO) if not isinstance(r, fontes_vault.Ignorada)]


def test_o_catalogo_versionado_cabe_nas_colunas():
    """No LIMITED field of the real catalog exceeds what Postgres accepts."""
    registros = _registros()
    assert len(registros) > 1000, "o catálogo veio vazio — o teste não estaria conferindo nada"

    # Only those the COLUMN limits. `titulo`, `descricao` and `dicas` are TEXT and
    # return `None` here — if one of them becomes VARCHAR again, it gets in on its own.
    limitados = {c: fs._limite(c) for c in DO_VAULT if fs._limite(c) is not None}
    assert limitados, "nenhum campo limitado — o teste não estaria conferindo nada"

    estouros: list[str] = []
    for registro in registros:
        for campo, limite in limitados.items():
            valor = getattr(registro, campo, None)
            if limite is not None and valor is not None and len(str(valor)) > limite:
                estouros.append(
                    f"{registro.instituicao}/{registro.type_name}: `{campo}` tem "
                    f"{len(str(valor))} caracteres, a coluna aceita {limite}"
                )

    assert not estouros, (
        f"{len(estouros)} registro(s) do catálogo não cabem no banco. O SQLite dos outros "
        f"testes aceita e o PostgreSQL recusa, abortando o LOTE inteiro da importação — foi "
        f"assim que 75 % do catálogo sumiu de produção. Primeiros casos:\n  "
        + "\n  ".join(estouros[:5])
    )


def test_o_titulo_de_fato_precisa_de_TEXT():
    """The premise of `titulo` as TEXT (scripts/init_schema.sql; the historical
    migration `a3c81d7e2f46` made the change), pinned against the real data.

    If one day the catalog no longer has long titles, this test fails — and then
    the question "do we still need TEXT?" deserves to be asked again, instead of
    the answer staying valid out of inertia.
    """
    registros = _registros()
    longos = [r for r in registros if r.titulo and len(r.titulo) > 255]
    assert longos, "nenhum título passa de 255 — reveja se TEXT ainda se justifica"
    assert FonteDeDados.__table__.c["titulo"].type.__class__.__name__ == "Text"
