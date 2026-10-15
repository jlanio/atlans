# app/services/contrato_do_subfluxo.py
"""A sub-workflow's contract, seen from the workflows that call it.

A workflow called by others declares its contract in the `ports` of its
SubWorkflowInput and SubWorkflowOutput nodes (`extract_contract`). The callers
wire against those names: an edge leaving their SubWorkflow node names an output
port as `from_key`, and an input port arrives as an `inputsMapping` key or as the
`to_key` of an edge arriving at the node. Nothing pins them — the run reads the
child's CURRENT definition — so renaming or removing a port in the child broke
every caller in silence: the edge delivers nothing, the input is dropped by the
child's allowlist.

The choice was to warn and validate, not to pin versions. One check on each side:

- saving the child (`PUT /workflows/{id}`): `portas_removidas` and
  `avisos_aos_pais` list the callers that use what the save removed. The save is
  never blocked by it.
- validating a caller (MCP): `contratos_dos_filhos` and
  `diagnosticos_de_contrato` check its edges at each SubWorkflow node against the
  child's contract — what `WorkflowExecutor.validate_edges` skips, because the
  executor never reads another workflow.

Both only read workflows of the SAME workspace: execution requires the child to
be there (`validate_subworkflow_references_against_db`), and reading a caller or
a child from another workspace would leak another tenant's definition.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from sqlalchemy import select

from app.core.utils.logger import get_logger
from app.core.utils.workflow_nodes import node_props
from app.models.workflow import Workflow
from app.services.workflow_move_report import chamadores_no_workspace
from flow.utils.workflow_contract import extract_contract

logger = get_logger(__name__)


def _chamadas(definition: Dict[str, Any]) -> Iterator[Tuple[Dict[str, Any], Dict[str, Any], str]]:
    """`(node, properties, workflowHash)` of each SubWorkflow node that names a target.

    `node_props`, like the move report: it also reads the canvas format
    (`data.properties`), where reading only `properties` would miss the call.
    """
    for no in definition.get("nodes") or []:
        if not isinstance(no, dict) or no.get("name") != "SubWorkflow":
            continue
        props = node_props(no)
        alvo = str(props.get("workflowHash") or "").strip()
        if alvo:
            yield no, props, alvo


def _mapeamento(bruto: Any) -> Dict[str, Any]:
    """`inputsMapping` as a dict.

    The editor stores it as JSON text (`setNodeField` only takes primitives) and
    the run decodes it (`_coerce_structured`). Reading only a dict here — as
    `collect_subworkflow_references` does — would miss every caller wired in the
    editor.
    """
    if isinstance(bruto, str):
        try:
            bruto = json.loads(bruto)
        except ValueError:
            return {}
    return bruto if isinstance(bruto, dict) else {}


def _nomes(contrato: Dict[str, Any], lado: str) -> Set[str]:
    return {p["name"] for p in contrato.get(lado) or []}


# The SubWorkflow node's envelope output, the dict of all the child's ports
# (`RESULT_KEY` in flow/nodes/control/sub_workflow.py, not imported here: that
# module loads the whole node registry).
_ENVELOPE = "subWorkflowResult"


def _chave_de_entrada(aresta: Dict[str, Any]) -> Optional[str]:
    """The key an edge delivers into the node: its `to_key`, else its `from_key`
    (`resolve_edge_inputs`). None for an edge that spreads everything."""
    return aresta.get("to_key") or _chave_de_saida(aresta)


def _chave_de_saida(aresta: Dict[str, Any]) -> Optional[str]:
    """The `from_key` the run delivers on an edge (`from_key_efetiva`).

    An edge the editor saved from port `r2` with the envelope as key reads as
    `r2` in the run: it is the port that edge uses, not the envelope.
    """
    # Here and not at the top: `flow.executor` pulls the whole engine in.
    from flow.executor.edge_resolver import from_key_efetiva

    return from_key_efetiva(aresta)


# ── Saving the child ──────────────────────────────────────────────────────────

def portas_removidas(antes: Any, depois: Any) -> Tuple[Set[str], Set[str]]:
    """`(outputs, inputs)` the contract of definition `antes` declared and the
    one of `depois` no longer honours — a renamed port counts as removed.

    Pure, so the PUT knows before any query whether there is anyone to warn: a
    workflow that is not a sub-workflow, or a save that keeps or only adds
    ports, ends here. The PUT calls it before saving, so a definition too
    malformed to read a contract from means "nothing to compare" — a warning
    must never be what fails a save.
    """
    try:
        velho = extract_contract(antes if isinstance(antes, dict) else {})
        novo = extract_contract(depois if isinstance(depois, dict) else {})
    except (AttributeError, TypeError):
        return set(), set()
    saidas = _nomes(velho, "outputs") - _nomes(novo, "outputs")
    entradas = _nomes(velho, "inputs") - _nomes(novo, "inputs")
    # Without a SubWorkflowOutput the child has no output at all: the caller's
    # SubWorkflow node fails at run ("não declara saída"), whatever edge leaves
    # it — even a passthrough output, which declared no port to compare. The
    # envelope joins the removed names, and `avisos_aos_pais` lists every caller.
    if velho["has_output_node"] and not novo["has_output_node"]:
        saidas = _nomes(velho, "outputs") | {_ENVELOPE}
    # A SubWorkflowInput left with no ports is passthrough again: it hands the
    # child every key a caller sends, so nothing those callers map is dropped.
    # The output has no such twin — with no ports it returns whatever reaches it
    # inside the child, and nothing promises the names the callers read.
    if novo["has_input_node"] and not novo["inputs"]:
        entradas = set()
    return saidas, entradas


async def avisos_aos_pais(
    db, id_hash: str, workspace_id: Optional[str], saidas: Set[str], entradas: Set[str],
) -> List[Dict[str, Any]]:
    """The callers in `workspace_id` that use a removed port: one notice per
    caller node and side, `{workflow_id, workflow_name, node_id, side, ports,
    edges}` (`SubworkflowNotice`).

    `saida`: edges leaving the caller's SubWorkflow node name a removed output in
    `from_key` (what the run reads) or, without one, in `source_handle` (what
    anchors the line on the canvas). `entrada`: the node feeds a removed input.
    A caller that only uses ports that still exist is not listed.

    One query, and none when nothing was removed. Never raises: the save it
    reports on is already committed, and a failure here must not turn it into an
    error — it costs the warning, and says so in the log.
    """
    if not (saidas or entradas) or not workspace_id:
        return []
    try:
        avisos: List[Dict[str, Any]] = []
        for pai_hash, pai_nome, pai_def, _ in await chamadores_no_workspace(db, id_hash, workspace_id):
            arestas = [e for e in pai_def.get("edges") or [] if isinstance(e, dict)]
            for no, props, alvo in _chamadas(pai_def):
                if alvo != id_hash:
                    continue
                nid = no.get("id")

                # A `from_key` decides what the edge delivers; a stale handle next
                # to a valid one is re-anchored by the editor from the `from_key`.
                saindo = [
                    e for e in arestas
                    if e.get("source") == nid and (_chave_de_saida(e) or e.get("source_handle")) in saidas
                ]
                portas_s = sorted({_chave_de_saida(e) or e.get("source_handle") for e in saindo})
                if _ENVELOPE in saidas:
                    # The output node itself is gone: the node fails at run
                    # whatever leaves it, so the caller is listed in any case.
                    saindo = [e for e in arestas if e.get("source") == nid]
                    portas_s = sorted(saidas)

                mapa = _mapeamento(props.get("inputsMapping"))
                if mapa:
                    # With a mapping only the mapped keys reach the child
                    # (sub_workflow.py, step 4): its KEYS are the child's ports, and
                    # an arriving edge's `to_key` names the caller's own key — the
                    # edges stay as they are, the mapping is what needs fixing.
                    portas_e, n_e = sorted(k for k in mapa if k in entradas), 0
                else:
                    # The key the edge delivers: its `to_key`, or its
                    # `from_key` without one — the child's allowlist drops
                    # either, even with a single declared input.
                    chegando = [e for e in arestas if e.get("target") == nid and _chave_de_entrada(e) in entradas]
                    portas_e, n_e = sorted({_chave_de_entrada(e) for e in chegando}), len(chegando)

                for lado, portas, n in (("saida", portas_s, len(saindo)), ("entrada", portas_e, n_e)):
                    if portas:
                        avisos.append({
                            # Text: a hand-written definition may carry a numeric
                            # id, and the response is validated AFTER the commit.
                            "workflow_id": pai_hash, "workflow_name": pai_nome,
                            "node_id": None if nid is None else str(nid),
                            "side": lado, "ports": portas, "edges": n,
                        })
    except Exception as exc:
        logger.warning(
            "Falha ao procurar quem chama o sub-fluxo %s com portas removidas: %s",
            id_hash, exc, exc_info=True,
        )
        return []
    # Stable: within a caller, its nodes keep the definition's order.
    avisos.sort(key=lambda a: (a["workflow_name"] or "", a["workflow_id"]))
    return avisos


# ── Validating a caller ───────────────────────────────────────────────────────

async def contratos_dos_filhos(db, definition: Dict[str, Any], workspace_id: str) -> Dict[str, Dict[str, Any]]:
    """`{workflowHash: contract}` of the ACTIVE workflows `definition` calls in
    `workspace_id`, in one query.

    A target that is missing, inactive, in the trash or in another workspace is
    left out: the reference check already refuses it, and the workspace filter
    is what keeps the ports of another tenant's workflow out of this report.
    """
    alvos = sorted({alvo for _, _, alvo in _chamadas(definition)})
    if not alvos or not workspace_id:
        return {}
    linhas = (await db.execute(
        select(Workflow.id_hash, Workflow.definition).where(
            Workflow.id_hash.in_(alvos),
            Workflow.workspace_id == workspace_id,
            Workflow.flag_ative.is_(True),
            Workflow.deleted_at.is_(None),
        )
    )).all()
    return {h: extract_contract(d if isinstance(d, dict) else {}) for h, d in linhas}


def diagnosticos_de_contrato(
    definition: Dict[str, Any], contratos: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Diagnostics of the edges at each SubWorkflow node against its child's
    contract, in the shape of `WorkflowExecutor.validate_edges` (the report reads
    both the same way):

    - `from_key` leaving the node that is neither a child output nor
      `subWorkflowResult` → error `edge_from_key_unknown`: the run delivers
      nothing on that edge (`resolve_edge_inputs` omits a missing key);
    - `from_key: subWorkflowResult` while the child declares outputs → warning
      `edge_subworkflow_envelope`: it delivers the dict of every port, and a
      node expecting a layer gets a dict;
    - a key arriving that the child drops → warning `edge_to_key_unknown`:
      with an `inputsMapping`, one the mapping does not read (only mapped keys
      reach the child); without one, a `to_key` that is not a child input (the
      child's allowlist).

    A child that declares no port on a side says nothing about that side: it is
    passthrough there, and what goes through depends on what arrives.
    """
    # Here and not at the top: importing a node module loads the whole node
    # registry, which validation only loads when it runs.
    from flow.nodes.control.sub_workflow import RESULT_KEY

    chamadas = {}
    for no, props, alvo in _chamadas(definition):
        contrato = contratos.get(alvo)
        if contrato is not None:
            chamadas[no.get("id")] = (alvo, contrato, _mapeamento(props.get("inputsMapping")))

    diagnosticos: List[Dict[str, Any]] = []
    for e in definition.get("edges") or []:
        if not isinstance(e, dict):
            continue
        origem, destino = e.get("source"), e.get("target")

        if origem in chamadas:
            alvo, contrato, _ = chamadas[origem]
            saidas = _nomes(contrato, "outputs")
            chave = _chave_de_saida(e)
            if chave and saidas and chave == RESULT_KEY:
                diagnosticos.append({
                    "severity": "warning", "code": "edge_subworkflow_envelope",
                    "source": origem, "target": destino, "from_key": chave,
                    "message": (
                        f"aresta de '{origem}' usa from_key '{RESULT_KEY}', que entrega o dict "
                        f"com todas as saídas do sub-fluxo ({sorted(saidas)}), não o valor de uma "
                        "delas: um nó que espera uma camada recebe o dict. Use o nome da porta "
                        "como from_key."
                    ),
                })
            elif chave and saidas and chave not in saidas:
                diagnosticos.append({
                    "severity": "error", "code": "edge_from_key_unknown",
                    "source": origem, "target": destino, "from_key": chave,
                    "message": (
                        f"from_key '{chave}' não é uma saída do sub-fluxo '{alvo}' chamado em "
                        f"'{origem}': a execução não entrega nada por esta aresta. Saídas: "
                        f"{sorted(saidas)} (e '{RESULT_KEY}', o dict com todas)."
                    ),
                })

        if destino in chamadas:
            alvo, contrato, mapa = chamadas[destino]
            entradas = _nomes(contrato, "inputs")
            if mapa:
                # With a mapping only the keys it reads reach the child
                # (sub_workflow.py builds the child's inputs from it alone): an
                # arriving key the mapping does not read is dropped, even one
                # named like a child input. The key is the edge's `to_key`, or
                # its `from_key` without one.
                chave = e.get("to_key") or _chave_de_saida(e)
                lidas = {v for v in mapa.values() if isinstance(v, str)}
                if chave and chave not in lidas:
                    diagnosticos.append({
                        "severity": "warning", "code": "edge_to_key_unknown",
                        "source": origem, "target": destino,
                        "message": (
                            f"a entrada '{chave}' de '{destino}' não é lida pelo inputsMapping "
                            f"(lê: {sorted(lidas)}): com mapeamento, só as chaves mapeadas chegam "
                            f"ao sub-fluxo '{alvo}', e esta é descartada."
                        ),
                    })
            else:
                # The key the edge delivers (`to_key`, else `from_key`): the
                # child's allowlist drops it either way.
                chave = _chave_de_entrada(e)
                if chave and entradas and chave not in entradas:
                    diagnosticos.append({
                        "severity": "warning", "code": "edge_to_key_unknown",
                        "source": origem, "target": destino,
                        "message": (
                            f"a entrada '{chave}' não é uma entrada do sub-fluxo '{alvo}' chamado em "
                            f"'{destino}': o sub-fluxo descarta a chave. Entradas: {sorted(entradas)}. "
                            "Indique a porta em to_key."
                        ),
                    })
    return diagnosticos
