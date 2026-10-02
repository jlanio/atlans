# tests/unit/test_validate_service.py
"""
`validar_definicao` chamada direto, sem HTTP — o contrato do service.

As tools do servidor MCP (`validate_workflow` e a validação antes de gravar)
consomem esta função; o que estes testes fixam é o que elas herdam dela: a
sessão de banco NÃO abre sem credencial nem workspace, `properties` e
`parameters` são aceitos como sinônimos, o `workspace_id` explícito vence o do
corpo (o MCP resolve id-ou-nome antes de chamar), quem não é membro recebe 403
antes de qualquer credencial, definição fatal sobe como `DefinicaoInvalidaError`
carregando o relatório, e registry vazio é 503 (falha de boot, não da
definição). O relatório em detalhe fica em `test_validate_report.py`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.exceptions import DefinicaoInvalidaError
from app.services.validate_service import WorkflowDefinition, validar_definicao

NS = "app.services.validate_service"
USUARIO = "usr-test-001"


def _no(id_hash: str, name: str, tipo: str = "datasource", **params) -> dict:
    return {"id": id_hash, "name": name, "type": tipo, "parameters": params}


def _sem_sessao():
    """Qualquer tentativa de abrir sessão derruba o teste."""
    return patch(f"{NS}.get_session_async", MagicMock(side_effect=AssertionError("sessão de banco aberta")))


def _sessao_falsa():
    db = MagicMock()
    resultado = MagicMock()
    resultado.all.return_value = []
    db.execute = AsyncMock(return_value=resultado)

    @asynccontextmanager
    async def _ctx():
        yield db

    return patch(f"{NS}.get_session_async", _ctx)


def _simulacao_falsa(saidas: dict | None = None, visto: dict | None = None):
    """Substitui o `simulate_runner` real; `visto` recebe o nó `n1` como o executor o vê."""
    from flow.executor.core import WorkflowExecutor

    async def _fake(self):
        if visto is not None:
            visto.update(self.node_mgr.node_defs["n1"])
        self.simulated_outputs = dict(saidas or {})
        return self.simulated_outputs

    return patch.object(WorkflowExecutor, "simulate_runner", _fake)


# ══════════════════════════════════════════════════════════════════════════════
# Caso comum — sem banco
# ══════════════════════════════════════════════════════════════════════════════

async def test_sem_credencial_nem_workspace_nao_abre_sessao():
    with _sem_sessao(), _simulacao_falsa({"n1": {"status": "ok", "schema": []}}):
        saida = await validar_definicao(
            {"nodes": [_no("n1", "ReadGeoJSON")], "edges": []}, user_id=USUARIO, workspace_id=None,
        )

    assert saida["n1"] == {"status": "ok", "schema": []}
    assert saida["__report__"]["ok"] is True
    assert "__edge_diagnostics__" not in saida


async def test_dict_e_modelo_sao_aceitos_e_properties_e_sinonimo_de_parameters():
    """Um `dict` passa pelo mesmo `WorkflowDefinition` do endpoint: `properties`
    (formato persistido) funde em `parameters` (formato do corpo) e o executor
    recebe os dois apontando para o MESMO dict; `alias` sobrevive."""
    visto_dict: dict = {}
    visto_modelo: dict = {}
    no = {"id": "n1", "name": "ReadGeoJSON", "type": "datasource",
          "properties": {"path": "x.geojson"}, "alias": "Caixa", "position": {"x": 1, "y": 2}}

    with _sem_sessao():
        with _simulacao_falsa(visto=visto_dict):
            await validar_definicao({"nodes": [no], "edges": []}, user_id=USUARIO, workspace_id=None)
        with _simulacao_falsa(visto=visto_modelo):
            await validar_definicao(
                WorkflowDefinition.model_validate({"nodes": [no], "edges": []}),
                user_id=USUARIO, workspace_id=None,
            )

    for visto in (visto_dict, visto_modelo):
        assert visto["parameters"] == {"path": "x.geojson"}
        assert visto["properties"] is visto["parameters"]
        assert visto["alias"] == "Caixa"
        assert "position" not in visto


async def test_parameters_vence_properties_em_conflito():
    visto: dict = {}
    no = {"id": "n1", "name": "ReadGeoJSON", "type": "datasource",
          "properties": {"path": "antigo.geojson", "so_aqui": 1}, "parameters": {"path": "novo.geojson"}}

    with _sem_sessao(), _simulacao_falsa(visto=visto):
        await validar_definicao({"nodes": [no], "edges": []}, user_id=USUARIO, workspace_id=None)

    assert visto["parameters"] == {"path": "novo.geojson", "so_aqui": 1}


async def test_sem_workspace_o_relatorio_sugere_informar_um():
    from app.services.validate_service import HINT_WORKSPACE

    with _sem_sessao(), _simulacao_falsa():
        saida = await validar_definicao(
            {"nodes": [_no("n1", "ReadGeoJSON")], "edges": []}, user_id=USUARIO, workspace_id=None,
        )

    assert HINT_WORKSPACE in saida["__report__"]["hints"]


# ══════════════════════════════════════════════════════════════════════════════
# workspace_id — explícito vence o corpo; filiação antes de tudo
# ══════════════════════════════════════════════════════════════════════════════

async def test_workspace_id_explicito_vence_o_do_corpo():
    papel = AsyncMock(return_value="operator")
    subfluxo = AsyncMock(return_value=[])

    with _sessao_falsa(), _simulacao_falsa(), \
         patch(f"{NS}.get_workspace_member_role", papel), \
         patch(f"{NS}.disabled_names", AsyncMock(return_value=set())), \
         patch(f"{NS}.validate_subworkflow_references_against_db", subfluxo):
        saida = await validar_definicao(
            {"nodes": [_no("n1", "ReadGeoJSON")], "edges": [], "workspace_id": "ws-do-corpo"},
            user_id=USUARIO, workspace_id="ws-explicito",
        )

    assert papel.await_args.args[1:] == ("ws-explicito", USUARIO)
    assert subfluxo.await_args.kwargs["workspace_id"] == "ws-explicito"
    # Com workspace, a dica de informar um não faz sentido.
    assert saida["__report__"]["hints"] == []


async def test_workspace_id_none_deixa_valer_o_do_corpo():
    """`None` aqui é "use o que veio na definição" — o campo opcional do corpo."""
    papel = AsyncMock(return_value="owner")

    with _sessao_falsa(), _simulacao_falsa(), \
         patch(f"{NS}.get_workspace_member_role", papel), \
         patch(f"{NS}.disabled_names", AsyncMock(return_value=set())), \
         patch(f"{NS}.validate_subworkflow_references_against_db", AsyncMock(return_value=[])):
        await validar_definicao(
            {"nodes": [_no("n1", "ReadGeoJSON")], "edges": [], "workspace_id": "ws-do-corpo"},
            user_id=USUARIO, workspace_id=None,
        )

    assert papel.await_args.args[1:] == ("ws-do-corpo", USUARIO)


async def test_nao_membro_do_workspace_e_403_antes_das_credenciais():
    guarda = AsyncMock()

    with _sessao_falsa(), _simulacao_falsa(), \
         patch(f"{NS}.get_workspace_member_role", AsyncMock(return_value=None)), \
         patch(f"{NS}.assert_credentials_accessible", guarda):
        with pytest.raises(HTTPException) as exc:
            await validar_definicao(
                {"nodes": [_no("n1", "DatabaseSpatialQuery",
                               credential_id="8d3f7b1e-2c44-4a5a-9f0e-1b2c3d4e5f60", query="SELECT 1")],
                 "edges": []},
                user_id=USUARIO, workspace_id="ws-alheio",
            )

    assert exc.value.status_code == 403
    guarda.assert_not_awaited()


async def test_papel_operator_leva_o_workspace_ao_escopo_da_simulacao():
    from contextlib import contextmanager

    escopos: list = []

    # `credential_scope` é um context manager síncrono; o dublê precisa ser também.
    @contextmanager
    def _escopo(*args, **kwargs):
        escopos.append((args, kwargs))
        yield

    with _sessao_falsa(), _simulacao_falsa(), \
         patch(f"{NS}.get_workspace_member_role", AsyncMock(return_value="operator")), \
         patch(f"{NS}.disabled_names", AsyncMock(return_value=set())), \
         patch(f"{NS}.validate_subworkflow_references_against_db", AsyncMock(return_value=[])), \
         patch(f"{NS}.credential_scope", _escopo):
        await validar_definicao(
            {"nodes": [_no("n1", "ReadGeoJSON")], "edges": []}, user_id=USUARIO, workspace_id="ws-1",
        )

    assert escopos == [(({USUARIO},), {"shared_workspace_id": "ws-1"})]


async def test_credencial_de_tipo_errado_ou_vencida_vira_erro_antes_do_executar():
    """Acessível não é usável: a resolução deixa de fora, em silêncio, a
    credencial de um tipo que o nó não aceita e a vencida — e o nó só recusava
    na execução, por "credencial não resolvida". Erro onde o nó consome o
    segredo injetado (WFS, banco); aviso onde ele usa o próprio id (DataOutput),
    porque ali a execução segue e só o download é recusado — e um erro
    impediria o assistente de gravar uma edição em outro nó."""
    import flow.nodes.datasource.database_spatial_query  # noqa: F401 — registra os nós
    import flow.nodes.datasource.wfs  # noqa: F401
    import flow.nodes.outputs.data_output  # noqa: F401

    cid_pg, cid_vencida = "8d3f7b1e-2c44-4a5a-9f0e-1b2c3d4e5f60", "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05"
    cid_authkey, cid_token_vencido = "1a2b3c4d-0000-4000-8000-000000000001", "1a2b3c4d-0000-4000-8000-000000000002"
    catalogo = AsyncMock(return_value={
        cid_pg: ("postgresql", "valida", None),
        cid_vencida: ("geoserver_authkey", "expirada", "2020-01-01T00:00:00Z"),
        cid_authkey: ("geoserver_authkey", "valida", None),
        cid_token_vencido: ("webhook_token", "expirada", "2020-01-01T00:00:00Z"),
    })
    saidas = {n: {"status": "ok", "schema": []} for n in ("n1", "n2", "n3", "n4")}
    with _sessao_falsa(), _simulacao_falsa(saidas), \
         patch(f"{NS}.assert_credentials_accessible", AsyncMock()), \
         patch(f"{NS}.tipos_e_validades", catalogo), \
         patch(f"{NS}.disabled_names", AsyncMock(return_value=set())):
        saida = await validar_definicao(
            {"nodes": [_no("n1", "WFS", url="https://geo.x/ows", typeName="ns:a", credential_id=cid_pg),
                       _no("n2", "WFS", url="https://geo.x/ows", typeName="ns:b", credential_id=cid_vencida.upper()),
                       # Nó de banco não declara `credential_types`: a FORMA da credencial decide.
                       _no("n3", "DatabaseSpatialQuery", query="SELECT 1", credential_id=cid_authkey),
                       _no("n4", "DataOutput", "output", isPublic=False, credential_id=cid_token_vencido)],
             "edges": []},
            user_id=USUARIO, workspace_id=None,
        )

    report = saida["__report__"]
    assert {(e["code"], e["node_id"]) for e in report["errors"]} == {
        ("credential_type_mismatch", "n1"), ("credential_expired", "n2"), ("credential_type_mismatch", "n3"),
    }
    assert report["ok"] is False
    assert "geoserver_authkey, wfs" in report["errors"][0]["message"]
    assert "não declara `http_auth`" in next(e["message"] for e in report["errors"] if e["node_id"] == "n3")
    (aviso,) = [w for w in report["warnings"] if w["code"] == "credential_expired"]
    assert aviso["node_id"] == "n4" and "download" in aviso["message"]
    assert catalogo.await_args.args[1] == {cid_pg, cid_vencida.upper(), cid_authkey, cid_token_vencido}


@pytest.mark.parametrize("expires_at, validade", [
    (None, "valida"), ("", "valida"),
    ("2099-01-01T00:00:00Z", "valida"), ("2099-01-01T00:00:00", "valida"),
    ("2020-01-01T00:00:00Z", "expirada"), ("2020-01-01T00:00:00-03:00", "expirada"),
    ("lixo", "invalida"),
])
def test_validade_da_credencial_e_a_regra_da_resolucao(expires_at, validade):
    from app.core.authorization.credential_loader import validade_da_credencial

    assert validade_da_credencial(expires_at) == validade


# ══════════════════════════════════════════════════════════════════════════════
# Erros estruturados
# ══════════════════════════════════════════════════════════════════════════════

async def test_definicao_fatal_sobe_como_definicao_invalida_com_report():
    with _sem_sessao(), pytest.raises(DefinicaoInvalidaError) as exc:
        await validar_definicao(
            {"nodes": [_no("n1", "NoQueNaoExiste", "action")], "edges": []}, user_id=USUARIO, workspace_id=None,
        )

    erro = exc.value
    assert erro.status_code == 422
    assert erro.report["ok"] is False
    assert erro.report["errors"][0]["code"] == "unknown_node"
    assert erro.report["errors"][0]["node_id"] == "n1"
    assert erro.report["disabled_nodes"] is None
    assert "não encontrado para instância" in erro.detail


async def test_registry_vazio_e_503():
    # `patch.dict(..., clear=True)` esvazia e restaura o MESMO dict. Trocar o
    # objeto (`patch(..., {})`) deixaria `flow.factory`, que prendeu o dict
    # original no import, olhando para um registry que este teste nunca limpou
    # — e qualquer `register_node` executado na janela do patch se perderia,
    # fazendo o resultado depender da ordem dos arquivos na suíte.
    with _sem_sessao(), patch.dict("flow.registry.NODE_REGISTRY", clear=True):
        with pytest.raises(HTTPException) as exc:
            await validar_definicao(
                {"nodes": [_no("n1", "ReadGeoJSON")], "edges": []}, user_id=USUARIO, workspace_id=None,
            )

    assert exc.value.status_code == 503


# ══════════════════════════════════════════════════════════════════════════════
# Catálogo de fontes — avisos sem rede
# ══════════════════════════════════════════════════════════════════════════════

_AVISO_DESCONHECIDA = {
    "code": "unknown_source", "severity": "warning", "node_id": "n1", "edge": None,
    "message": "nó 'WFS' (id=n1) aponta para url+typeName que não estão no catálogo.",
}


def _wfs(id_hash="n1"):
    return _no(id_hash, "WFS", url="https://geoserver.funai.gov.br/geoserver/ows", typeName="Funai:tis_poligonais")


def _banco_para_o_catalogo(conferir):
    """Sessão falsa + o que a validação com workspace consulta, com o catálogo dublado."""
    return (
        _sessao_falsa(),
        patch(f"{NS}.get_workspace_member_role", AsyncMock(return_value="editor")),
        patch(f"{NS}.disabled_names", AsyncMock(return_value=set())),
        patch(f"{NS}.validate_subworkflow_references_against_db", AsyncMock(return_value=[])),
        patch(f"{NS}.fontes_service.conferir_fontes_da_definicao", conferir),
    )


async def test_wfs_fora_do_catalogo_vira_aviso_e_nao_derruba_o_ok():
    from contextlib import ExitStack

    from app.services.validate_service import HINT_FONTES

    conferir = AsyncMock(return_value=[_AVISO_DESCONHECIDA])
    with ExitStack() as pilha:
        for p in _banco_para_o_catalogo(conferir):
            pilha.enter_context(p)
        pilha.enter_context(_simulacao_falsa())
        saida = await validar_definicao(
            {"nodes": [_wfs()], "edges": []}, user_id=USUARIO, workspace_id="ws-1",
        )

    report = saida["__report__"]
    assert report["ok"] is True and report["errors"] == []
    assert _AVISO_DESCONHECIDA in report["warnings"]
    assert HINT_FONTES in report["hints"]
    # O catálogo recebe os nós no formato do executor e o descriptor do WFS
    # (com `source_kind`), no workspace da validação.
    nos, descritores, ws = conferir.await_args.args[1:]
    assert nos[0]["name"] == "WFS" and descritores["WFS"]["source_kind"] == "wfs" and ws == "ws-1"


async def test_fonte_catalogada_nao_gera_aviso_nem_dica():
    from contextlib import ExitStack

    from app.services.validate_service import HINT_FONTES

    with ExitStack() as pilha:
        for p in _banco_para_o_catalogo(AsyncMock(return_value=[])):
            pilha.enter_context(p)
        pilha.enter_context(_simulacao_falsa())
        saida = await validar_definicao({"nodes": [_wfs()], "edges": []}, user_id=USUARIO, workspace_id="ws-1")

    report = saida["__report__"]
    assert report["warnings"] == [] and HINT_FONTES not in report["hints"]


async def test_catalogo_indisponivel_nao_derruba_a_validacao():
    from contextlib import ExitStack

    with ExitStack() as pilha:
        for p in _banco_para_o_catalogo(AsyncMock(side_effect=RuntimeError("catálogo fora"))):
            pilha.enter_context(p)
        pilha.enter_context(_simulacao_falsa())
        saida = await validar_definicao({"nodes": [_wfs()], "edges": []}, user_id=USUARIO, workspace_id="ws-1")

    assert saida["__report__"]["ok"] is True and saida["__report__"]["warnings"] == []


async def test_sem_workspace_o_catalogo_nao_e_consultado():
    """Sem a filiação provada não há catálogo de workspace a olhar — e nada de sessão."""
    conferir = AsyncMock(return_value=[_AVISO_DESCONHECIDA])
    with _sem_sessao(), _simulacao_falsa(), patch(f"{NS}.fontes_service.conferir_fontes_da_definicao", conferir):
        saida = await validar_definicao({"nodes": [_wfs()], "edges": []}, user_id=USUARIO, workspace_id=None)

    conferir.assert_not_awaited()
    assert saida["__report__"]["warnings"] == []
