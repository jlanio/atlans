# tests/unit/test_artifacts_busca_por_workflow.py
"""A busca de /artifacts tem de casar com o NOME DO WORKFLOW.

Quando a busca era no cliente, ela varria `workflow_name`, `output_key` e
`filename`. Ao empurra-la para o SQL (necessario: a pagina deixou de baixar a
colecao inteira) o nome do fluxo ficou de fora — e ele e a coluna mais visivel
da tabela. Digitar 'Cadastro Ambiental' devolvia "Nenhum artefato encontrado"
com as linhas daquele fluxo visiveis um segundo antes, e sem colecao local nao
sobra nada para casar no cliente.
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


async def _listar(**kwargs):
    """Chama a rota direto. Os defaults declarados como `Query(...)` nao sao
    resolvidos fora do FastAPI, entao precisam vir explicitos."""
    db = _db()
    await list_artifacts(
        db=db, workspace_ids=["ws-1"], kind=None, limit=50, offset=0, **kwargs
    )
    return db, [str(c.args[0]) for c in db.execute.await_args_list]


@pytest.mark.asyncio
async def test_busca_cobre_nome_do_workflow_alem_de_filename_e_output_key():
    _, (sql_count, sql_itens) = await _listar(search="Cadastro")

    for sql in (sql_count, sql_itens):
        assert "workflows.name" in sql
        assert "artifacts.filename" in sql
        assert "artifacts.output_key" in sql


@pytest.mark.asyncio
async def test_contagem_faz_o_mesmo_join_da_pagina():
    """Sem o join na contagem, o `total` seria calculado sobre um filtro que
    referencia `workflows.name` sem a tabela na query — erro de SQL — ou, pior,
    um total incoerente com a pagina exibida."""
    _, (sql_count, _) = await _listar(search="Cadastro")

    assert "JOIN workflows" in sql_count


@pytest.mark.asyncio
async def test_sem_busca_a_contagem_nao_paga_o_join():
    """O join existe para a busca; a contagem do caso comum (sem `search`) nao
    deve arrastar `workflows` junto."""
    _, (sql_count, _) = await _listar(search=None)

    assert "workflows" not in sql_count


@pytest.mark.asyncio
async def test_curingas_do_usuario_continuam_escapados():
    """`%` e `_` sao literais: sem escape, buscar por '_' varreria tudo."""
    _, (sql_count, _) = await _listar(search="a_b%c")

    parametros = sql_count  # o termo vai como bind; o ESCAPE fica no SQL
    assert "ESCAPE" in parametros.upper()
