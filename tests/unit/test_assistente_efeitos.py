"""The assistant's own workflows run without a click only while they do not act
outside (full-project review, assistant block).

What dies if any of these fails:

- The Home creating AND running a workflow with SendEmail / SendWebhook /
  HttpRequest / a stored credential with no click at all — the model's prompt
  (fed untrusted text) was the only barrier.
- The confirmation card not saying WHICH nodes act (`efeitos`).
- A probe/register of a URL outside the catalog going out without a click.
- The detector failing open on a node type it does not know.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.mcp.escopo import ASSISTANT_SCOPES
from app.services import assistente_superficie as ag
from app.services.assistente_efeitos import nos_que_agem
from app.services.assistente_service import EstadoDoLaco, Evento

from ._mcp_harness import FakeRedis, fake_scope

pytestmark = pytest.mark.asyncio

CATALOGADA = "https://geoserver.exemplo.gov.br/ows"


@pytest.fixture(autouse=True)
def catalogo_basico(monkeypatch):
    """The catalog knows CATALOGADA; any other literal URL is outside it."""
    from app.services import fontes_service

    async def _no_catalogo(_db, _escopo, url):
        return fontes_service.normalize_url(url) == CATALOGADA

    @asynccontextmanager
    async def _sessao():
        yield object()

    monkeypatch.setattr(fontes_service, "url_no_catalogo", _no_catalogo)
    monkeypatch.setattr(ag.infra, "sessao", _sessao)


def _no(nid, nome, **props):
    return {"id": nid, "name": nome, "type": "x", "properties": props}


LE_E_TRANSFORMA = {"nodes": [
    _no("n1", "WFS", url=CATALOGADA, typeName="a:b"),
    _no("n2", "Buffer", distance=10),
    _no("n3", "DataOutput"),
], "edges": []}

MANDA_EMAIL = {"nodes": [*LE_E_TRANSFORMA["nodes"], _no("n4", "SendEmail", toAddresses="x@exemplo.org")], "edges": []}


# ── the detector ─────────────────────────────────────────────────────────────


async def test_reading_and_transforming_does_not_act():
    assert nos_que_agem(LE_E_TRANSFORMA) == []


@pytest.mark.parametrize(
    "no, esperado",
    [
        (_no("e", "SendEmail"), "SendEmail (e)"),
        (_no("w", "SendWebhook"), "SendWebhook (w)"),
        (_no("s", "SaveToPostGIS"), "SaveToPostGIS (s)"),
        (_no("p", "PublishMap"), "PublishMap (p)"),
        (_no("g", "SaveGeoJSON"), "SaveGeoJSON (g)"),
        # A GET carries data in its query string too.
        (_no("h", "HttpRequest", method="GET"), "HttpRequest (h)"),
        (_no("sub", "SubWorkflow", workflowHash="wf-x"), "SubWorkflow (sub)"),
        (_no("t", "ScheduleTrigger", cron="* * * * *"), "ScheduleTrigger (t)"),
        (_no("wh", "WebhookTrigger"), "WebhookTrigger (wh)"),
        # Reads, but with the person's stored secret.
        (_no("q", "DatabaseQuery", credential_id="cred-1"), "DatabaseQuery (q)"),
        # Writes into the shared Drive (and may overwrite a file others read).
        (_no("d", "DataOutput", context="drive", overwrite=True), "DataOutput (d)"),
        (_no("d2", "DataOutput", context="{{ inputs.destino }}"), "DataOutput (d2)"),
        # The run's data can leave in the query string of a templated URL.
        (_no("u", "WFS", url="https://x.example/ows?f={{ n1.output }}"), "WFS (u)"),
        (_no("i", "DataInput", context="url", url="https://x.example/{{ n1.output }}"), "DataInput (i)"),
        # Unknown to the registry: no way to tell it is harmless.
        (_no("z", "NoQueNaoExiste"), "NoQueNaoExiste (z)"),
    ],
)
async def test_what_acts_outside(no, esperado):
    assert nos_que_agem({"nodes": [_no("n1", "WFS"), no]}) == [esperado]


async def test_the_canvas_format_with_data_is_read_too():
    definicao = {"nodes": [{"id": "n9", "type": "custom", "data": {"name": "SendWebhook", "properties": {}}}]}
    assert nos_que_agem(definicao) == ["SendWebhook (n9)"]


@pytest.mark.parametrize("definicao", [None, {}, {"nodes": []}, {"nodes": [1, None]}])
async def test_nothing_to_run_acts_on_nothing(definicao):
    assert nos_que_agem(definicao) == []


@pytest.mark.parametrize("definicao", ["x", 7, {"nodes": "x"}])
async def test_an_unreadable_definition_acts(definicao):
    """Fail closed: the tool parses strings itself, so judging only dicts let
    a string through (fix review)."""
    from app.services.assistente_efeitos import ILEGIVEL
    assert nos_que_agem(definicao) == [ILEGIVEL]


async def test_a_definition_sent_as_a_json_string_is_judged_like_a_dict():
    import json
    assert nos_que_agem(json.dumps(MANDA_EMAIL)) == ["SendEmail (n4)"]


@pytest.mark.parametrize(
    "no",
    [
        _no("d", "DataOutput", credential_id="cred-1"),        # the download token
        _no("c", "CartaImagem", credential_id="cred-1"),       # a run artifact too
        _no("d3", "DataOutput", context="artifacts"),
    ],
)
async def test_what_only_produces_the_run_artifact_does_not_act(no):
    assert nos_que_agem({"nodes": [no]}) == []


async def test_a_trigger_counts_when_creating_not_when_running():
    gatilho = {"nodes": [_no("t", "ScheduleTrigger", cron="* * * * *"), _no("o", "DataOutput")]}
    assert nos_que_agem(gatilho) == ["ScheduleTrigger (t)"]
    assert nos_que_agem(gatilho, disparos=False) == []


# ── the Home gate ────────────────────────────────────────────────────────────


def _estado(redis=None):
    eventos: list[Evento] = []

    async def emitir(ev):
        eventos.append(ev)

    escopo = fake_scope(
        user_id="usr-1", scopes=ASSISTANT_SCOPES, origem_dos_fluxos="assistente", todos_os_workspaces=True,
    )
    return EstadoDoLaco(escopo=escopo, redis=redis or FakeRedis(), conversa_id="conv-1", emitir=emitir), eventos


def _confirmacoes(eventos):
    return [e for e in eventos if e.tipo == "confirmacao"]


async def test_creating_a_workflow_that_only_reads_needs_no_click():
    estado, eventos = _estado()
    veredito = await ag._home_gate(estado, "create_workflow", {"name": "x", "definition": LE_E_TRANSFORMA}, "tu-1")
    assert veredito is None and not eventos


async def test_creating_a_workflow_that_sends_email_asks_for_the_click_and_says_why():
    redis = FakeRedis()
    estado, eventos = _estado(redis)
    veredito = await ag._home_gate(estado, "create_workflow", {"name": "x", "definition": MANDA_EMAIL}, "tu-1")
    assert veredito == (ag.AWAITING_MESSAGE, False)
    (card,) = _confirmacoes(eventos)
    assert card.dados["acao"]["tool"] == "create_workflow"
    assert card.dados["acao"]["efeitos"] == ["SendEmail (n4)"]
    # The replay shows the same reason: it is stored with the confirmation.
    import json
    (guardado,) = redis.dados.values()
    assert json.loads(guardado)["efeitos"] == ["SendEmail (n4)"]
    # What the click will execute is what was stored, with the whole definition.
    assert len(redis.dados) == 1


@pytest.fixture
def fluxo_do_assistente(monkeypatch):
    """`carregar_workflow` returns an assistant workflow with the definition in the dict."""
    alvo = {"definition": LE_E_TRANSFORMA, "origem": "assistente"}

    @asynccontextmanager
    async def _sessao():
        yield object()

    async def _carregar(db, escopo, ref, **kw):
        return SimpleNamespace(origem=alvo["origem"], definition=alvo["definition"]), "editor"

    monkeypatch.setattr(ag.infra, "sessao", _sessao)
    monkeypatch.setattr(ag, "carregar_workflow", _carregar)
    return alvo


async def test_running_its_own_harmless_workflow_needs_no_click(fluxo_do_assistente):
    estado, eventos = _estado()
    assert await ag._home_gate(estado, "run_workflow", {"workflow_id": "wf-a"}, "tu-1") is None
    assert not eventos


async def test_running_its_own_workflow_that_acts_asks_for_the_click(fluxo_do_assistente):
    fluxo_do_assistente["definition"] = MANDA_EMAIL
    estado, eventos = _estado()
    veredito = await ag._home_gate(estado, "run_workflow", {"workflow_id": "wf-a"}, "tu-1")
    assert veredito == (ag.AWAITING_MESSAGE, False)
    assert len(_confirmacoes(eventos)) == 1


async def test_updating_its_own_workflow_judges_the_NEW_definition(fluxo_do_assistente):
    estado, eventos = _estado()
    # harmless stored, acting new → click
    veredito = await ag._home_gate(
        estado, "update_workflow", {"workflow_id": "wf-a", "definition": MANDA_EMAIL}, "tu-1"
    )
    assert veredito is not None and len(_confirmacoes(eventos)) == 1

    # acting stored, harmless new → free (the run after it is free too)
    fluxo_do_assistente["definition"] = MANDA_EMAIL
    estado, eventos = _estado()
    veredito = await ag._home_gate(
        estado, "update_workflow", {"workflow_id": "wf-a", "definition": LE_E_TRANSFORMA}, "tu-2"
    )
    assert veredito is None and not eventos

    # rename only: the stored definition decides
    estado, eventos = _estado()
    veredito = await ag._home_gate(estado, "update_workflow", {"workflow_id": "wf-a", "name": "novo"}, "tu-3")
    assert veredito is not None and len(_confirmacoes(eventos)) == 1


async def test_the_persons_workflow_still_always_asks(fluxo_do_assistente):
    fluxo_do_assistente["origem"] = "usuario"
    estado, eventos = _estado()
    assert await ag._home_gate(estado, "run_workflow", {"workflow_id": "wf-p"}, "tu-1") is not None
    assert len(_confirmacoes(eventos)) == 1


# ── probing outside the catalog ──────────────────────────────────────────────


@pytest.fixture
def catalogo(monkeypatch):
    from app.services import fontes_service

    conhecidas = {"https://geoserver.exemplo.gov.br/ows"}
    chamadas = []

    async def _no_catalogo(db, escopo, url):
        chamadas.append(url)
        return fontes_service.normalize_url(url) in conhecidas

    @asynccontextmanager
    async def _sessao():
        yield object()

    monkeypatch.setattr(fontes_service, "url_no_catalogo", _no_catalogo)
    monkeypatch.setattr(ag.infra, "sessao", _sessao)
    return chamadas


@pytest.mark.parametrize("ferramenta", ["probe_source", "register_source"])
async def test_a_cataloged_endpoint_is_probed_without_a_click(catalogo, ferramenta):
    estado, eventos = _estado()
    args = {"url": "https://geoserver.exemplo.gov.br/ows?service=WFS", "type_name": "a:b"}
    assert await ag._home_gate(estado, ferramenta, args, "tu-1") is None
    assert not eventos and catalogo


@pytest.mark.parametrize("ferramenta", ["probe_source", "register_source"])
@pytest.mark.parametrize("url", ["https://outro.exemplo.net/wfs?x=1", "", None, "ftp://x"])
async def test_an_endpoint_outside_the_catalog_asks_for_the_click(catalogo, ferramenta, url):
    estado, eventos = _estado()
    veredito = await ag._home_gate(estado, ferramenta, {"url": url, "type_name": "a:b"}, "tu-1")
    assert veredito == (ag.AWAITING_MESSAGE, False)
    assert len(_confirmacoes(eventos)) == 1


async def test_a_catalog_lookup_failure_asks_for_the_click(monkeypatch):
    from app.services import fontes_service

    async def _quebra(*_a, **_k):
        raise RuntimeError("banco fora")

    @asynccontextmanager
    async def _sessao():
        yield object()

    monkeypatch.setattr(fontes_service, "url_no_catalogo", _quebra)
    monkeypatch.setattr(ag.infra, "sessao", _sessao)
    estado, eventos = _estado()
    veredito = await ag._home_gate(estado, "probe_source", {"url": "https://geoserver.exemplo.gov.br/ows"}, "tu-1")
    assert veredito is not None and len(_confirmacoes(eventos)) == 1


async def test_a_string_definition_does_not_slip_past_the_gate():
    """The MCP SDK parses a JSON-string argument back into a dict before the tool
    runs: the gate has to judge it the same way (fix review)."""
    import json
    estado, eventos = _estado()
    args = {"name": "x", "definition": json.dumps(MANDA_EMAIL)}
    assert await ag._home_gate(estado, "create_workflow", args, "tu-1") is not None
    assert _confirmacoes(eventos)[0].dados["acao"]["efeitos"] == ["SendEmail (n4)"]


async def test_reading_a_url_outside_the_catalog_asks_for_the_click():
    """Creating and running a WFS of an uncatalogued URL is the same request a
    probe_source would ask a click for."""
    estado, eventos = _estado()
    fora = {"nodes": [_no("w", "WFS", url="https://outro.exemplo.net/wfs", typeName="a:b"), _no("o", "DataOutput")]}
    assert await ag._home_gate(estado, "create_workflow", {"name": "x", "definition": fora}, "tu-1") is not None
    assert _confirmacoes(eventos)[0].dados["acao"]["efeitos"] == ["WFS (w)"]


async def test_the_run_card_says_which_stored_nodes_act(fluxo_do_assistente):
    """The run's arguments carry no definition: the card shows the STORED one's
    acting nodes, so the person sees why the click is asked."""
    fluxo_do_assistente["definition"] = MANDA_EMAIL
    estado, eventos = _estado()
    await ag._home_gate(estado, "run_workflow", {"workflow_id": "wf-a"}, "tu-1")
    assert _confirmacoes(eventos)[0].dados["acao"]["efeitos"] == ["SendEmail (n4)"]


async def test_running_a_workflow_with_a_schedule_trigger_is_free(fluxo_do_assistente):
    """Running creates no schedule: the trigger only counts on create/update."""
    fluxo_do_assistente["definition"] = {"nodes": [*LE_E_TRANSFORMA["nodes"], _no("t", "ScheduleTrigger")]}
    estado, eventos = _estado()
    assert await ag._home_gate(estado, "run_workflow", {"workflow_id": "wf-a"}, "tu-1") is None
    assert not eventos
