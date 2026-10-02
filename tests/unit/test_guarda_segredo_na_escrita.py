"""Segredo nao entra na definition pelas bordas de escrita da REST.

Credencial mora em `credentials`, cifrada; a definition guarda o `credential_id`
e o servidor injeta o valor numa COPIA no despacho. Um segredo escrito na
definition ficaria cifrado no banco, mas ja teria viajado por transporte e log —
e a redacao da saida o apagaria depois, dando a falsa impressao de que ele nao
esta la.

O servidor MCP ja recusava nas suas tres tools de construcao
(`app/mcp/tools/construcao.py`); a REST, que e por onde o editor grava, nao. Um
levantamento em producao (2026-09-14) mediu 286 nos, 56 com `credential_id` e
ZERO segredos gravados: a recusa torna invariante um estado que ja era verdade
por convencao, sem recusar nada do que existe.

Os testes chamam as funcoes de rota direto, sem cliente HTTP: o que se prova
aqui e a guarda, e as dependencias (papel, sessao) so atrapalhariam.
"""
import pytest
from fastapi import HTTPException

from app.api.routers import workflows_router as WR

SEGREDO = "postgresql://usuario:senha-secretissima@host:5432/base"  # pragma: allowlist secret
TOKEN = "sk-ZmFrZS10b2tlbi1wYXJhLXRlc3RlLTEyMzQ1Ng"  # pragma: allowlist secret


def _no(props: dict) -> dict:
    return {"nodes": [{"id": "n1", "name": "DatabaseQuery", "properties": props}]}


# ── A recusa ────────────────────────────────────────────────────────────────

def test_connection_string_literal_e_recusada():
    with pytest.raises(HTTPException) as exc:
        WR._recusar_segredo(_no({"connectionString": SEGREDO}))

    assert exc.value.status_code == 422
    assert "credential_id" in exc.value.detail


def test_cabecalho_de_autorizacao_tambem_e_recusado():
    """Decisao explicita do dono: cabecalho livre entra na recusa.

    Quem precisa mandar token em header cria credencial. Nao ha excecao nem
    modo "so avisa" — e o caminho por credencial ja existe (`http_auth`).
    """
    with pytest.raises(HTTPException) as exc:
        WR._recusar_segredo(_no({"headers": {"Authorization": f"Bearer {TOKEN}"}}))

    assert exc.value.status_code == 422


def test_a_recusa_cita_o_caminho_e_nunca_o_valor():
    """A mensagem de recusa nao pode ser o vazamento que ela evita."""
    with pytest.raises(HTTPException) as exc:
        WR._recusar_segredo(_no({"connectionString": SEGREDO}))

    detalhe = str(exc.value.detail)
    assert "connectionString" in detalhe          # o caminho, para o usuario achar
    assert SEGREDO not in detalhe                 # o valor, nunca
    assert "senha-secretissima" not in detalhe


# ── O que NAO pode ser recusado ─────────────────────────────────────────────

def test_expressao_pura_passa():
    """`{{ ... }}` e referencia resolvida em runtime, nao segredo gravado."""
    WR._recusar_segredo(_no({"connectionString": "{{ inputs.dsn }}"}))


def test_so_o_esquema_de_autenticacao_passa():
    """"Bearer {{ $Cred.token }}" nao grava nada — sobra so o esquema."""
    WR._recusar_segredo(_no({"headers": {"Authorization": "Bearer {{ $Cred.token }}"}}))


def test_referencia_por_credential_id_passa():
    """O caminho pretendido: a definition guarda a referencia, nao o valor."""
    WR._recusar_segredo(_no({
        "credential_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
        "query": "SELECT * FROM lotes",
    }))


def test_definition_vazia_passa():
    WR._recusar_segredo({})
    WR._recusar_segredo(None)


# ── A fiacao das rotas ──────────────────────────────────────────────────────

async def test_update_sem_definition_nao_dispara_a_guarda(monkeypatch):
    """A regressao mais provavel: `WorkflowUpdate` e PARCIAL.

    `definition` ausente significa "nao mexe nela". Uma guarda distraida, que
    checasse sem testar a ausencia, barraria ate renomear um workflow — e o
    sintoma (nao consigo salvar o nome) nao apontaria para segredo nenhum.
    """
    from app.schemas.workflow import WorkflowUpdate

    chamado = []
    monkeypatch.setattr(WR, "_recusar_segredo", lambda d: chamado.append(d))

    gravado = {}

    class _Service:
        async def update_workflow(self, id_hash, workflow_in, **kw):
            gravado["nome"] = workflow_in.name
            return {"id_hash": id_hash}

    class _Wf:
        id_hash = "wf-1"
        workspace_id = "ws-1"

    # O papel é conferido pela dependência da rota (`workflow_com_papel`), que
    # a chamada direta não passa; aqui só o limiter atrapalha.
    monkeypatch.setattr(WR.limiter, "enabled", False)

    class _User:
        id_hash = "u-1"

    await WR.update_workflow(
        request=None,
        workflow_in=WorkflowUpdate(name="nome novo"),
        service=_Service(),
        wf=_Wf(),
        db=None,
        current_user=_User(),
    )

    assert chamado == []                 # guarda nao foi consultada
    assert gravado["nome"] == "nome novo"  # e a edicao passou


def test_paridade_com_a_borda_do_mcp():
    """A REST nao pode ser mais permissiva que o servidor MCP.

    As duas chamam `definition_contem_segredo`; este teste quebra se alguem
    criar uma segunda lista de chaves para um dos lados.
    """
    from app.mcp.tools.construcao import _recusar_segredo as mcp_recusa

    definicao = _no({"headers": {"Authorization": f"Bearer {TOKEN}"}})

    with pytest.raises(HTTPException):
        WR._recusar_segredo(definicao)
    with pytest.raises(Exception):           # o MCP levanta ToolError, nao HTTP
        mcp_recusa(definicao)


# ── A guarda esta LIGADA nas rotas ──────────────────────────────────────────
#
# Sem estes, a funcionalidade inteira podia ser removida das rotas e a suite
# continuava verde: os testes acima exercitam o helper, nao a fiacao. Foi
# exatamente o que uma revisao mediu — apagar as chamadas (eram tres; a de
# /workflows/validate saiu com a rota) nao mexia num unico nome na suite.

class _Usuario:
    id_hash = "u-1"


class _Wf:
    id_hash = "wf-1"
    workspace_id = "ws-1"


@pytest.fixture
def rota_liberada(monkeypatch):
    """Tira do caminho o que nao e o assunto: limiter e papel.

    Nas rotas `/{id_hash}` o papel e da dependencia (`workflow_com_papel`), que
    a chamada direta nao passa; no POST ele e conferido no corpo da rota, e
    aqui a pessoa e `editor` — a comparacao roda de verdade.
    """
    from app.core.authorization import workflow_access

    async def _papel(db, ws_id, uid):
        return "editor"

    monkeypatch.setattr(WR.limiter, "enabled", False)
    monkeypatch.setattr(workflow_access, "get_workspace_member_role", _papel)


async def test_rota_de_criacao_recusa(rota_liberada):
    from app.schemas.workflow import WorkflowCreate

    payload = WorkflowCreate(
        name="fluxo", workspace_id="ws-1", definition=_no({"connectionString": SEGREDO}),
    )

    with pytest.raises(HTTPException) as exc:
        await WR.create_workflow(
            request=None, payload=payload, service=None, current_user=_Usuario(), db=None,
        )
    assert exc.value.status_code == 422
    assert SEGREDO not in str(exc.value.detail)


async def test_rota_de_atualizacao_recusa(rota_liberada):
    from app.schemas.workflow import WorkflowUpdate

    with pytest.raises(HTTPException) as exc:
        await WR.update_workflow(
            request=None,
            workflow_in=WorkflowUpdate(definition=_no({"connectionString": SEGREDO})),
            service=None,
            wf=_Wf(),
            db=None,
            current_user=_Usuario(),
        )
    assert exc.value.status_code == 422


async def test_params_schema_tambem_e_guardado(rota_liberada):
    """Coluna irma, gravavel no mesmo corpo, e que NAO e cifrada no banco."""
    from app.schemas.workflow import WorkflowUpdate

    with pytest.raises(HTTPException) as exc:
        await WR.update_workflow(
            request=None,
            workflow_in=WorkflowUpdate(params_schema={"token": {"type": "string", "default": TOKEN}}),
            service=None,
            wf=_Wf(),
            db=None,
            current_user=_Usuario(),
        )
    assert exc.value.status_code == 422
    assert TOKEN not in str(exc.value.detail)


# ── Os falsos positivos ACEITOS ─────────────────────────────────────────────

@pytest.mark.parametrize("caso,props", [
    ("bind :token numa query SQL",
     {"query": "SELECT * FROM t WHERE x = :token", "queryParams": {"token": "abc123"}}),
    ("renomear uma COLUNA chamada senha",
     {"renameFields": {"senha": "senha_hash"}}),
    ("webhook declarando o formato do payload",
     {"payload_schema": {"token": "string", "valor": "number"}}),
    ("token de paginacao num body JSON",
     {"body": {"pagina": 2, "token": "eyJhbGciOiJIUzI1NiJ9"}}),
])
def test_recusas_deliberadas_em_mapas_de_dado_do_usuario(caso, props):
    """Quatro padroes LEGITIMOS que a guarda recusa — e isso foi decidido.

    A regra casa por NOME DE CHAVE, e nestes mapas a chave e dado do usuario:
    nome de bind, nome de coluna, nome de campo do payload. Uma revisao mediu
    30 definitions realistas e achou exatamente estes quatro.

    A alternativa — isentar `queryParams`, `renameFields`, `payload_schema` e
    `body` da regra por nome — foi considerada e RECUSADA: um token de verdade
    colado ali passaria em silencio, e a deteccao ficaria mais estreita que a
    redacao, que segue redigindo esses caminhos. `redacao.py` proibe isso por
    escrito: "a borda aceita o que a entrega depois apaga".

    Este teste existe para que a proxima pessoa que topar com um 422 desses
    saiba que nao e bug. A saida e usar `credential_id`. Se voce veio aqui para
    fazer o teste passar afrouxando a regra, isso e decisao de produto — nao
    conserto.
    """
    with pytest.raises(HTTPException) as exc:
        WR._recusar_segredo(_no(props))
    assert exc.value.status_code == 422
