# tests/unit/test_artifacts_busca_por_workflow.py
"""The /artifacts search has to match the WORKFLOW NAME.

When the search ran on the client, it scanned `workflow_name`, `output_key` and
`filename`. When pushing it down to SQL (necessary: the page stopped downloading
the whole collection) the workflow name was left out — and it is the most visible
column of the table. Typing 'Cadastro Ambiental' returned "Nenhum artefato
encontrado" (no artifact found) with that workflow's rows visible a second
before, and without a local collection there is nothing left to match on the
client.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.routers.artifacts_router import list_artifacts


def _db():
    contagem = MagicMock()
    contagem.scalar.return_value = 0
    itens = MagicMock()
    itens.all.return_value = []
    return MagicMock(execute=AsyncMock(side_effect=[contagem, itens]))


async def _list_schedules(**kwargs):
    """Calls the route directly. Defaults declared as `Query(...)` are not
    resolved outside FastAPI, so they have to be passed explicitly."""
    db = _db()
    await list_artifacts(
        db=db, workspace_ids=["ws-1"], kind=None, limit=50, offset=0, **kwargs
    )
    return db, [str(c.args[0]) for c in db.execute.await_args_list]


@pytest.mark.asyncio
async def test_search_covers_workflow_name_besides_filename_and_output_key():
    _, (sql_count, sql_items) = await _list_schedules(search="Cadastro")

    for sql in (sql_count, sql_items):
        assert "workflows.name" in sql
        assert "artifacts.filename" in sql
        assert "artifacts.output_key" in sql


@pytest.mark.asyncio
async def test_count_does_the_same_join_as_the_page():
    """Without the join in the count, `total` would be computed over a filter that
    references `workflows.name` without the table in the query — an SQL error — or,
    worse, a total inconsistent with the page shown."""
    _, (sql_count, _) = await _list_schedules(search="Cadastro")

    assert "JOIN workflows" in sql_count


@pytest.mark.asyncio
async def test_without_search_the_count_does_not_pay_for_the_join():
    """The join exists for the search; the count in the common case (no `search`)
    must not drag `workflows` along."""
    _, (sql_count, _) = await _list_schedules(search=None)

    assert "workflows" not in sql_count


@pytest.mark.asyncio
async def test_user_wildcards_stay_escaped():
    """`%` and `_` are literals: without escaping, searching for '_' would match everything."""
    _, (sql_count, _) = await _list_schedules(search="a_b%c")

    parametros = sql_count  # the term goes as a bind; the ESCAPE stays in the SQL
    assert "ESCAPE" in parametros.upper()
