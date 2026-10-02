# tests/unit/test_mcp_resolucao.py
"""
Resolver nome ou id para um recurso — sem entregar o que o token não alcança.

Aceitar nome é o que torna as ferramentas usáveis por quem conversa ("rode o
Recorte mensal"), e é também onde um servidor desatento vaza informação: um
"não encontrado" diferente de um "proibido" já diz se o recurso existe do outro
lado do muro, e escolher "o primeiro" de dois homônimos faz a ferramenta agir
sobre algo que ninguém apontou.

O que este arquivo fixa:

- nome repetido vira `ambiguous` com os ids dos candidatos — nunca um palpite;
- workflow inexistente, workflow apagado e workflow de OUTRA conta respondem o
  mesmo `not_found`, com a mesma frase: a diferença entre "não existe" e
  "existe e você não alcança" é justamente o que um cliente com um laço de ids
  usaria para mapear o que há do outro lado;
- o alcance do TOKEN corta antes do papel do usuário: um token restrito a um
  workspace não enxerga o workflow do vizinho nem quando o dono é dono dos dois;
- com um workspace só no alcance, `workspace_id` é dispensável.

Banco SQLite em memória, porque o que se testa aqui SÃO as consultas.
"""
from __future__ import annotations

import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app.core.utils.datetime_utils import utc_now_naive
from app.mcp.resolucao import carregar_workflow, e_uuid, resolver_workspace
from app.models.workflow import Workflow
from app.models.workspace_member import WorkspaceMember
from tests.unit._mcp_harness import (
    banco_em_memoria,
    criar_usuario,
    criar_workspace,
    escopo_falso,
)

ID_A = "11111111-1111-4111-8111-111111111111"
ID_B = "22222222-2222-4222-8222-222222222222"


def corpo(exc: ToolError) -> dict:
    """O JSON que viaja dentro do `ToolError`."""
    return json.loads(str(exc))


async def criar_workflow(db, *, id_hash: str, nome: str, workspace_id: str, apagado=False) -> Workflow:
    wf = Workflow(
        id_hash=id_hash,
        name=nome,
        workspace_id=workspace_id,
        definition={"nodes": [], "edges": []},
        deleted_at=utc_now_naive() if apagado else None,
    )
    db.add(wf)
    await db.commit()
    return wf


async def tornar_membro(db, workspace_id: str, user_id: str, papel: str = "viewer") -> None:
    db.add(WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=papel))
    await db.commit()


@pytest.fixture
async def banco():
    """Dois workspaces do mesmo dono, para os casos de ambiguidade e de alcance."""
    async with banco_em_memoria() as fabrica:
        async with fabrica() as db:
            await criar_usuario(db, "usr-1", "ana")
            await criar_workspace(db, "ws-1", "usr-1", "Principal")
            await criar_workspace(db, "ws-2", "usr-1", "Secundário")
        yield fabrica


# ── e_uuid ────────────────────────────────────────────────────────────────────


def test_e_uuid_separa_identificador_de_nome():
    assert e_uuid(ID_A) is True
    assert e_uuid("Recorte mensal") is False
    assert e_uuid("") is False
    assert e_uuid(None) is False


# ── resolver_workspace ────────────────────────────────────────────────────────


async def test_workspace_unico_dispensa_o_parametro(banco):
    async with banco() as db:
        assert await resolver_workspace(db, escopo_falso(workspace_ids={"ws-1"}), None) == "ws-1"


async def test_com_dois_workspaces_a_omissao_vira_ambiguous_com_os_candidatos(banco):
    escopo = escopo_falso(workspace_ids={"ws-1", "ws-2"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolver_workspace(db, escopo, None)
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "ambiguous"
    assert {c["id"] for c in detalhe["candidates"]} == {"ws-1", "ws-2"}
    assert {c["name"] for c in detalhe["candidates"]} == {"Principal", "Secundário"}


async def test_workspace_por_nome_dentro_do_escopo(banco):
    escopo = escopo_falso(workspace_ids={"ws-1", "ws-2"})
    async with banco() as db:
        assert await resolver_workspace(db, escopo, "Secundário") == "ws-2"


async def test_nome_repetido_em_dois_workspaces_vira_ambiguous(banco):
    async with banco() as db:
        await criar_workspace(db, "ws-3", "usr-1", "Principal")
    escopo = escopo_falso(workspace_ids={"ws-1", "ws-3"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolver_workspace(db, escopo, "Principal")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "ambiguous"
    assert {c["id"] for c in detalhe["candidates"]} == {"ws-1", "ws-3"}


async def test_id_de_workspace_fora_do_escopo_e_proibido(banco):
    """Existe, o usuário é dono — mas o token não alcança.

    A referência tem forma de id (é um UUID, como todo `id_hash` do Atlans), e a
    recusa é `forbidden` sem consultar o banco: nenhuma consulta significa
    nenhuma chance de a resposta contar se aquele id existe.
    """
    async with banco() as db:
        await criar_workspace(db, ID_B, "usr-1", "Terceiro")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolver_workspace(db, escopo, ID_B)
    assert corpo(exc.value)["code"] == "forbidden"


async def test_nome_de_workspace_desconhecido_e_not_found(banco):
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolver_workspace(db, escopo, "Inexistente")
    assert corpo(exc.value)["code"] == "not_found"


async def test_token_sem_workspace_nenhum_e_proibido(banco):
    escopo = escopo_falso(workspace_ids=set())
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolver_workspace(db, escopo, None)
    assert corpo(exc.value)["code"] == "forbidden"


# ── carregar_workflow ─────────────────────────────────────────────────────────


async def test_carrega_por_id_e_devolve_o_papel(banco):
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        wf, papel = await carregar_workflow(db, escopo, ID_A)
    assert wf.id_hash == ID_A
    # Dono do workspace: o papel mais alto, acima de admin.
    assert papel == "owner"


async def test_carrega_por_nome(banco):
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_A, nome="Recorte mensal", workspace_id="ws-1")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        wf, _ = await carregar_workflow(db, escopo, "Recorte mensal")
    assert wf.id_hash == ID_A


async def test_nome_repetido_em_dois_workspaces_lista_os_ids(banco):
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
        await criar_workflow(db, id_hash=ID_B, nome="Recorte", workspace_id="ws-2")
    escopo = escopo_falso(workspace_ids={"ws-1", "ws-2"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Recorte")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "ambiguous"
    assert {c["id"] for c in detalhe["candidates"]} == {ID_A, ID_B}
    assert {c["workspace_id"] for c in detalhe["candidates"]} == {"ws-1", "ws-2"}


async def test_workflow_apagado_responde_not_found(banco):
    """A lixeira não é 403: para quem chama, o workflow não existe mais."""
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_A, nome="Antigo", workspace_id="ws-1", apagado=True)
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, ID_A)
    assert corpo(exc.value)["code"] == "not_found"
    # E o mesmo pela busca por nome.
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Antigo")
    assert corpo(exc.value)["code"] == "not_found"


async def test_id_inexistente_e_not_found_antes_de_qualquer_403(banco):
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "33333333-3333-4333-8333-333333333333")
    assert corpo(exc.value)["code"] == "not_found"


async def test_id_de_outra_conta_responde_byte_a_byte_como_id_inexistente(banco):
    """O oráculo de existência entre contas, fechado no texto e no código.

    O workflow existe, num workspace de outra conta, e o usuário não é membro.
    O núcleo responde 403 (e continua respondendo — a REST depende disso); aqui
    a resposta é a MESMA de um id que nunca existiu, byte a byte. Se sobrasse
    qualquer diferença — o `code`, uma palavra na frase, o `hint` —, quem
    tivesse um token de leitura poderia varrer identificadores e descobrir
    quais existem do outro lado do muro.
    """
    async with banco() as db:
        await criar_usuario(db, "usr-2", "bruno")
        await criar_workspace(db, "ws-9", "usr-2", "De outro")
        await criar_workflow(db, id_hash=ID_B, nome="Alheio", workspace_id="ws-9")
    escopo = escopo_falso(workspace_ids={"ws-1"})

    async with banco() as db:
        with pytest.raises(ToolError) as alheio:
            await carregar_workflow(db, escopo, ID_B)
    async with banco() as db:
        with pytest.raises(ToolError) as inexistente:
            await carregar_workflow(db, escopo, "33333333-3333-4333-8333-333333333333")

    assert corpo(alheio.value)["code"] == "not_found"
    assert str(alheio.value) == str(inexistente.value)
    # E a referência recebida não volta na mensagem: ecoar o id seria o mesmo
    # oráculo por outra porta (a frase distinguiria as duas chamadas).
    assert ID_B not in str(alheio.value)


async def test_nome_de_workflow_fora_do_escopo_nao_revela_existencia(banco):
    """Pelo nome a resposta é `not_found`: o filtro do escopo entra na consulta."""
    async with banco() as db:
        await criar_usuario(db, "usr-2", "bruno")
        await criar_workspace(db, "ws-9", "usr-2", "De outro")
        await criar_workflow(db, id_hash=ID_B, nome="Alheio", workspace_id="ws-9")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Alheio")
    assert corpo(exc.value)["code"] == "not_found"


async def test_token_restrito_nao_ve_workspace_do_proprio_dono(banco):
    """O dono alcança os dois workspaces; o token, só um. Vence o token.

    É o caso que separa "o que o usuário pode" de "o que este token pode" — e o
    que impede que um token de leitura emitido para um projeto sirva de chave
    para todos os outros.

    Aqui a recusa é `forbidden`, e não o `not_found` do caso entre contas, de
    propósito: o recurso é da própria conta que emitiu o token, que já o vê na
    interface e com qualquer outro token seu. Não há existência a esconder de
    quem é dono dela — há um alcance a explicar, e dizer "este token não chega
    aqui" é o que evita meia hora procurando um workflow que não sumiu.
    """
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_B, nome="Do outro projeto", workspace_id="ws-2")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, ID_B)
    assert corpo(exc.value)["code"] == "forbidden"
    # Pelo nome, não aparece sequer como existente.
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Do outro projeto")
    assert corpo(exc.value)["code"] == "not_found"


async def test_membro_comum_carrega_com_o_papel_de_membro(banco):
    async with banco() as db:
        await criar_usuario(db, "usr-2", "bruno")
        await tornar_membro(db, "ws-1", "usr-2", "editor")
        await criar_workflow(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
    escopo = escopo_falso(user_id="usr-2", workspace_ids={"ws-1"})
    async with banco() as db:
        wf, papel = await carregar_workflow(db, escopo, ID_A)
    assert (wf.id_hash, papel) == (ID_A, "editor")


async def test_carregar_por_id_nao_decifra_por_padrao(banco, monkeypatch):
    """`decifrar=False` é o default: nada de definition em claro na sessão."""
    from app.services import workflow_service

    async def _nao_deveria(*args, **kwargs):  # pragma: no cover - o teste falha antes
        raise AssertionError("o caminho que decifra não pode ser usado pelo MCP")

    monkeypatch.setattr(
        workflow_service.WorkflowService, "get_workflow_by_hash", _nao_deveria, raising=True
    )
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        wf, _ = await carregar_workflow(db, escopo, ID_A)
    assert wf.id_hash == ID_A
