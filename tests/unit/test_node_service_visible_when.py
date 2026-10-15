"""
Regression: the nodes' properties declare `visibleWhen` (conditional
visibility), but the NodeProperty schema and the assembly in NodeService.list_nodes
didn't pass the key along — Pydantic dropped it and the frontend never received
it, leaving ALL fields always visible (DataInput's two pickers, DataOutput's
Bearer token even when public, etc.).

This test walks the service's real path and ensures `visibleWhen` reaches the
frontend serialized.
"""
from unittest.mock import patch

import pytest

from flow.registry import auto_discover_nodes
from app.services.node_service import NodeService

auto_discover_nodes()


async def _list():
    async def _no_disabled(_db):
        return set()

    with patch("app.services.node_service.disabled_names", _no_disabled):
        return await NodeService().list_nodes(db=None)


def _props(defs, node_name):
    for d in defs:
        if d.name == node_name:
            return {p.name: p for p in d.properties}
    raise AssertionError(f"no '{node_name}' ausente do catalogo")


@pytest.mark.asyncio
async def test_datainput_pickers_have_visible_when():
    defs = await _list()
    props = _props(defs, "DataInput")
    assert props["driveFileId"].visibleWhen == {"field": "context", "in": ["drive"]}
    assert props["artifactId"].visibleWhen == {"field": "context", "in": ["artifacts"]}
    # `context` and `crs` are always visible — no visibleWhen.
    assert props["context"].visibleWhen is None
    assert props["crs"].visibleWhen is None


@pytest.mark.asyncio
async def test_dataoutput_credential_and_public_have_visible_when():
    defs = await _list()
    props = _props(defs, "DataOutput")
    # isPublic: Artefatos (artifacts) context AND content that leaves the machine. An
    # artifact kept on the executor has no download, so there is no access to control.
    vw = props["isPublic"].visibleWhen
    assert isinstance(vw, list) and len(vw) == 2
    assert {"field": "context", "in": ["artifacts"]} in vw
    assert {"field": "localidade", "in": ["herdar"]} in vw

    # credential_id: the two above PLUS non-public.
    vw = props["credential_id"].visibleWhen
    assert isinstance(vw, list) and len(vw) == 3
    assert {"field": "context", "in": ["artifacts"]} in vw
    assert {"field": "localidade", "in": ["herdar"]} in vw
    assert any(r["field"] == "isPublic" and False in r["in"] for r in vw)


@pytest.mark.asyncio
async def test_locality_is_in_every_node_that_writes_an_artifact():
    """The `if` that chooses local vs cloud must not exist in a single node.

    That is how the policy was born — `keepLocal` on DataOutput and nothing
    else — and the result was an executor configured to retain data that kept
    sending everything the OTHER output nodes produced.
    """
    defs = await _list()
    for nome in ("DataOutput", "SaveGeoJSON", "SaveToGeoParquet", "SaveToShapefile", "SaveToS3", "CartaImagem", "SaveFile"):
        prop = _props(defs, nome).get("localidade")
        assert prop is not None, f"no '{nome}' sem o campo de localidade"
        assert prop.default == "herdar", f"no '{nome}': o padrao tem de ser herdar da maquina"
        # Without the option to send: it would be the only one able to override the
        # machine's policy, and the executor would silently ignore it.
        assert [o.value for o in prop.options] == ["herdar", "executor"], nome


@pytest.mark.asyncio
async def test_keeplocal_no_longer_exists_in_any_node():
    """Replaced by `localidade`, with no shim. If it showed up again in some
    node, `validate_node_parameters` would accept both and the policy would
    come to depend on which of them the workflow saved."""
    defs = await _list()
    for d in defs:
        assert all(p.name != "keepLocal" for p in d.properties), f"no '{d.name}'"


@pytest.mark.asyncio
async def test_output_node_registry_has_complete_serialization():
    """Sanity: model_dump doesn't lose visibleWhen (what FastAPI sends)."""
    defs = await _list()
    props = _props(defs, "DataInput")
    dumped = props["driveFileId"].model_dump(exclude_none=True)
    assert dumped.get("visibleWhen") == {"field": "context", "in": ["drive"]}


# ── Suggested column fields ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_column_fields_declare_where_the_suggestion_comes_from():
    """`suggest_columns` tells the editor WHICH input to look at to suggest column
    names. In Join the two keys come from different sides: suggesting A's
    columns in B's key field would be worse than suggesting nothing."""
    props = _props(await _list(), "AttributeJoin")
    assert props["keyA"].suggest_columns == "layerA"
    assert props["keyB"].suggest_columns == "layerB"
    assert props["columns"].suggest_columns == "layerB"


@pytest.mark.asyncio
async def test_single_input_node_suggests_from_all():
    props = _props(await _list(), "AttributeFilter")
    assert props["attributeName"].suggest_columns == "*"


@pytest.mark.asyncio
async def test_column_list_fields_became_chips_with_suggestion():
    """The fields that take SEVERAL columns declare type 'chips' (execute
    accepts a list, a JSON string and the old CSV) and `suggest_columns` so the
    editor offers the columns seen in the last run. None of these nodes has
    declared ports, so the suggestion is '*'.

    The DEFAULT matters for version compat: in fields that were type "string",
    it stays "" — an executor with an older flow/ still validates those fields
    as string, and a list in the default brought down the whole run just
    because the workflow had been saved in the new UI. RemoveDuplicates was
    already object/[] before, so [] there is what the old executor expects."""
    defs = await _list()
    for no, campo, default in (
        ("RemoveDuplicates", "fields", []),
        ("ChangeDetector", "fields", ""),
        ("ChangeDetector", "ignore_fields", ""),
        ("PublishMap", "visible_fields", ""),
    ):
        prop = _props(defs, no)[campo]
        assert prop.type == "chips", f"{no}.{campo}"
        assert prop.suggest_columns == "*", f"{no}.{campo}"
        assert prop.default == default, f"{no}.{campo}"


@pytest.mark.asyncio
async def test_setfields_suggests_columns_without_changing_the_type():
    """SetFields keeps type 'object' — a dedicated web helper consumes those
    fields — but all three declare `suggest_columns` so the suggestions block
    shows up there too."""
    props = _props(await _list(), "SetFields")
    for campo in ("setFields", "removeFields", "renameFields"):
        assert props[campo].type == "object", campo
        assert props[campo].suggest_columns == "*", campo


@pytest.mark.asyncio
async def test_sort_and_switch_suggest_columns_without_changing_the_type():
    """Sort.sort_by and Switch.rules got dedicated editors in the web app
    (field+direction / field+operator+value+output rows) that persist the SAME
    list execute reads — the type stays 'object' on purpose: changing the
    format would break saved workflows and old executors."""
    defs = await _list()
    for no, campo in (("Sort", "sort_by"), ("Switch", "rules")):
        prop = _props(defs, no)[campo]
        assert prop.type == "object", f"{no}.{campo}"
        assert prop.suggest_columns == "*", f"{no}.{campo}"


@pytest.mark.asyncio
async def test_every_string_field_asking_for_a_column_declares_a_suggestion():
    """The node census found `string` fields that ask for a COLUMN NAME without
    the marker — the operator saw the hint in the filter and nothing in the
    Dissolve next to it, which looked like flakiness. Pins the ones with a
    single input (suggesting from all ports is correct by construction)."""
    defs = await _list()
    for no, campo in [
        ("Dissolve", "byColumn"),
        ("Conditional", "fieldName"),
        ("GeocodeNode", "address_column"),
    ]:
        assert _props(defs, no)[campo].suggest_columns == "*", f"{no}.{campo}"


@pytest.mark.asyncio
async def test_field_unrelated_to_column_declares_nothing():
    """The absence matters: the editor only shows the suggestions block where it
    makes sense, and marking everything would turn the hint into noise."""
    props = _props(await _list(), "AttributeJoin")
    assert props["how"].suggest_columns is None
    assert props["seDuplicado"].suggest_columns is None


# ── The defect class, closed for good ────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_declared_key_is_lost_along_the_way():
    """NodeService copies the properties field by field (`p.get('x')`), and a
    forgotten line makes the descriptor declare something the frontend never
    receives. It already happened with `visibleWhen` (the reason for this
    file), with `dynamic_inputs`, and again with `suggest_columns`.

    Instead of one more test per key, this one walks the WHOLE catalog: for
    each property, every key the descriptor declares AND the schema knows has
    to arrive with the same value.
    """
    from flow.registry import NODE_REGISTRY
    from app.schemas.node import NodeProperty

    conhecidas = set(NodeProperty.model_fields)
    # `model_dump` is what allows comparing data with data: nested fields
    # (a select's `options`) arrive as a Pydantic model, and comparing the
    # model with the descriptor's raw dict would flag the catalog's 34 selects.
    served = {
        d.name: {p.name: p.model_dump() for p in d.properties}
        for d in await _list()
    }

    perdidas: list[str] = []
    for nome, cls in NODE_REGISTRY.items():
        if nome not in served:
            continue  # node disabled in the test environment
        for bruta in (cls.description().get("properties") or []):
            servida = served[nome].get(bruta.get("name"))
            if servida is None:
                continue
            for chave in set(bruta) & conhecidas:
                if servida.get(chave) != bruta[chave]:
                    perdidas.append(f"{nome}.{bruta['name']}.{chave}")

    assert not perdidas, (
        "chaves declaradas no descriptor que nao chegam ao frontend: "
        + ", ".join(sorted(perdidas))
    )


# ── TOP-LEVEL flags of NodeDefinition (outside `properties`) ─────────────────

def _def(defs, node_name):
    for d in defs:
        if d.name == node_name:
            return d
    raise AssertionError(f"no '{node_name}' ausente do catalogo")


@pytest.mark.asyncio
async def test_subworkflowinput_exposes_outputs_from_ports():
    """The sub-workflow trigger declares `outputs_from_ports`: it is what makes the
    editor derive ONE output per declared port and, with that, makes the key
    selector on the edge ('escolher') appear. Without passing the flag through
    the catalog, the trigger goes back to the anonymous handle/spreading and
    there is no way to choose what to pass along — that was exactly the
    reported defect."""
    d = _def(await _list(), "SubWorkflowInput")
    assert d.outputs_from_ports is True


@pytest.mark.asyncio
async def test_node_top_level_flags_are_not_lost():
    """The sibling of `test_no_declared_key_is_lost_along_the_way`, for
    NodeDefinition's TOP-LEVEL flags (they are not `properties`): a new flag in
    description() that NodeService forgets to map is dropped by Pydantic.
    It already happened with `dynamic_inputs` and again with
    `outputs_from_ports` (the trigger's key selector vanished). Walks the
    whole catalog."""
    from flow.registry import NODE_REGISTRY

    FLAGS = ("dynamic_inputs", "dynamic_output", "outputs_from_ports", "requires_credential")
    served = {d.name: d for d in await _list()}

    perdidas: list[str] = []
    for nome, cls in NODE_REGISTRY.items():
        servido = served.get(nome)
        if servido is None:
            continue  # node disabled in the test environment
        info = cls.description() or {}
        for flag in FLAGS:
            if flag in info and getattr(servido, flag) != bool(info[flag]):
                perdidas.append(f"{nome}.{flag}")

    assert not perdidas, (
        "flags de topo declaradas na description() que nao chegam ao frontend: "
        + ", ".join(sorted(perdidas))
    )
