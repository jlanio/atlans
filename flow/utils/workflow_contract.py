# flow/utils/workflow_contract.py
"""
Extrai o contrato (API publica) de um workflow para uso como sub-fluxo.

Contrato declarado via property `ports` (lista de strings) nos nodes
SubWorkflowInput e SubWorkflowOutput. As edges saindo do Input e chegando
no Output nao precisam ter `from_key`/`to_key` definidos — a unica edge
permitida em cada lado roteia o dict inteiro via `inputs.update(...)` no
executor (caminho "sem chave" em flow/executor/core.py).
"""
from __future__ import annotations

import json
from typing import Any, Dict


_INPUT_NODE_NAME = "SubWorkflowInput"
_OUTPUT_NODE_NAME = "SubWorkflowOutput"
_PORTS_PROP = "ports"


def _node_properties(node: Dict[str, Any]) -> Dict[str, Any]:
    """Retorna properties do node aceitando ambos os formatos do canvas:
    `node["properties"]` ou `node["data"]["properties"]`."""
    props = node.get("properties")
    if isinstance(props, dict):
        return props
    data = node.get("data") or {}
    return data.get("properties") or {}


def _parse_ports(raw: Any) -> list[str]:
    """Normaliza `ports` para list[str]. Aceita lista nativa ou JSON serializado
    (helper UI armazena via JSON.stringify para compatibilidade com setNodeField).
    Filtra valores vazios e nao-strings."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return []
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def extract_contract(definition: Dict[str, Any]) -> Dict[str, list]:
    """Retorna {"inputs": [{name, ...}], "outputs": [...], "has_input_node", "has_output_node"}.

    Inputs/outputs sao lidos da property `ports` dos nodes SubWorkflowInput
    e SubWorkflowOutput. Quando o workflow nao tem esses nodes, retorna
    listas vazias e flags has_*_node False — caller decide o que fazer.
    """
    nodes = definition.get("nodes") or []

    input_nodes = [n for n in nodes if n.get("name") == _INPUT_NODE_NAME]
    output_nodes = [n for n in nodes if n.get("name") == _OUTPUT_NODE_NAME]

    # Une portas de todos os nodes do tipo (raro ter mais de 1, mas defensivo).
    input_keys: list[str] = []
    seen_in: set[str] = set()
    for n in input_nodes:
        for key in _parse_ports(_node_properties(n).get(_PORTS_PROP)):
            if key not in seen_in:
                seen_in.add(key)
                input_keys.append(key)

    output_keys: list[str] = []
    seen_out: set[str] = set()
    for n in output_nodes:
        for key in _parse_ports(_node_properties(n).get(_PORTS_PROP)):
            if key not in seen_out:
                seen_out.add(key)
                output_keys.append(key)

    return {
        "inputs": [{"name": k, "type": "any", "description": None} for k in input_keys],
        "outputs": [{"name": k, "type": "any", "description": None} for k in output_keys],
        "has_input_node": bool(input_nodes),
        "has_output_node": bool(output_nodes),
        # Contagens: mais de um node de contrato torna o retorno ambíguo
        # (collect_subworkflow_output devolve só o primeiro).
        "input_node_count": len(input_nodes),
        "output_node_count": len(output_nodes),
    }


def validate_inputs_mapping(
    inputs_mapping: Dict[str, Any], contract: Dict[str, list]
) -> list[str]:
    """Retorna lista de mensagens de erro para chaves invalidas.

    Compara as chaves de `inputs_mapping` (que sao chaves do sub-fluxo) com
    as chaves declaradas em `contract["inputs"]`. Aceita mapping parcial
    (sub-fluxo pode receber subset).

    Returns lista vazia se OK; lista de mensagens caso contrario.
    """
    if not isinstance(inputs_mapping, dict):
        return []
    declared = {p["name"] for p in (contract.get("inputs") or [])}
    if not declared:
        # Sub-fluxo sem inputs declarados; nao temos como validar
        return []
    errors: list[str] = []
    for key in inputs_mapping.keys():
        if key not in declared:
            errors.append(
                f"Chave '{key}' nao existe no contrato do sub-fluxo. "
                f"Declaradas: {sorted(declared) or '<nenhuma>'}."
            )
    return errors


def collect_subworkflow_references(definition: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Lista todos os nodes SubWorkflow na definicao com seus workflowHash
    + inputsMapping. Usado para validacao cross-workflow ao salvar."""
    refs: list[Dict[str, Any]] = []
    for n in (definition.get("nodes") or []):
        if n.get("name") != "SubWorkflow":
            continue
        props = n.get("properties") or {}
        wh = (props.get("workflowHash") or "").strip()
        mapping = props.get("inputsMapping") or {}
        if not wh:
            continue
        refs.append({
            "node_id": n.get("id"),
            "workflow_hash": wh,
            "inputs_mapping": mapping if isinstance(mapping, dict) else {},
        })
    return refs


# Profundidade maxima da cadeia de sub-fluxos. O SubWorkflowNode importa daqui
# para poder EXPLICAR o estouro: sem a constante compartilhada, exceder o limite
# chegava ao operador como "workflow nao encontrado".
MAX_PROFUNDIDADE = 10


async def collect_subworkflow_definitions_recursive(
    root_definition: Dict[str, Any],
    db,
    workspace_id: str | None = None,
    max_depth: int = MAX_PROFUNDIDADE,
) -> Dict[str, Dict[str, Any]]:
    """Coleta recursivamente as definitions dos sub-workflows referenciados.

    Usado pelo servidor ao montar o envelope do job: o executor nao tem acesso
    ao DB, entao precisa receber tudo no payload. Inclui A -> B -> C -> D
    em uma unica passagem.

    Limita profundidade para evitar payloads gigantes em caso de cadeia
    excessiva (default 10 niveis — generoso para uso real).

    Returns {hash: definition_decifrada}. Hashes nao encontrados ou de
    outros workspaces sao silenciosamente ignorados — `validate_subworkflow_
    references_against_db` ja bloqueou esses casos no save.
    """
    from sqlalchemy import select
    from app.models.models import Workflow
    from app.core.utils.encryption import decrypt_workflow_connections

    collected: Dict[str, Dict[str, Any]] = {}
    visited: set[str] = set()
    queue: list[tuple[Dict[str, Any], int]] = [(root_definition, 0)]

    while queue:
        definition, depth = queue.pop(0)
        if depth >= max_depth:
            continue

        refs = collect_subworkflow_references(definition)
        new_hashes = [r["workflow_hash"] for r in refs if r["workflow_hash"] not in visited]
        if not new_hashes:
            continue
        visited.update(new_hashes)

        stmt = select(Workflow).where(Workflow.id_hash.in_(new_hashes))
        if workspace_id:
            stmt = stmt.where(Workflow.workspace_id == workspace_id)
        rows = (await db.execute(stmt)).scalars().all()

        for wf in rows:
            if not wf.flag_ative:
                continue
            try:
                decrypted = decrypt_workflow_connections(wf.definition or {})
            except Exception:
                decrypted = wf.definition or {}
            collected[wf.id_hash] = decrypted
            queue.append((decrypted, depth + 1))

    return collected


async def validate_subworkflow_references_against_db(
    definition: Dict[str, Any],
    db,
    workspace_id: str | None = None,
) -> list[str]:
    """Valida que cada SubWorkflow na `definition` referencia um workflow
    que (a) existe, (b) esta ativo, (c) tem contrato (SubWorkflowInput +
    SubWorkflowOutput), (d) `inputsMapping` so usa chaves declaradas.

    Retorna lista de mensagens de erro (vazia se OK). Pensada para ser
    chamada antes de salvar workflow A (POST/PUT) — bloqueia o save com
    422 se houver violacoes.

    Cross-workspace: se `workspace_id` for fornecido, a query já filtra pelo
    workspace do pai — um alvo de outro workspace é "nao existe", igual a um
    hash inventado. Distinguir "existe mas e de outro" de "nao existe" (ou de
    "esta desativado") seria um oraculo de existencia e estado de workflows
    alheios para qualquer membro (o hash e uuid4, mas o chamador pode ser um
    workspace criado so para consultar).
    """
    refs = collect_subworkflow_references(definition)
    if not refs:
        return []

    from sqlalchemy import select
    from app.models.models import Workflow
    from app.core.utils.encryption import decrypt_workflow_connections

    # Carrega TODOS os alvos numa unica query (evita N+1 quando o workflow A
    # tem multiplos SubWorkflows).
    hashes = {ref["workflow_hash"] for ref in refs}
    stmt = select(Workflow).where(Workflow.id_hash.in_(hashes))
    if workspace_id:
        stmt = stmt.where(Workflow.workspace_id == workspace_id)
    rows = (await db.execute(stmt)).scalars().all()
    targets_by_hash: dict[str, Workflow] = {w.id_hash: w for w in rows}

    errors: list[str] = []
    for ref in refs:
        wh = ref["workflow_hash"]
        node_id = ref["node_id"]
        target = targets_by_hash.get(wh)

        # A query ja filtrou por workspace; a segunda condicao e cinto e
        # suspensorio (uma sessao que devolva linhas de fora) e le como
        # inexistente ANTES de olhar o estado, para nao vazar nem isso.
        if target is None or (workspace_id and target.workspace_id != workspace_id):
            errors.append(
                f"Node SubWorkflow '{node_id}' aponta para workflow '{wh}' "
                "que nao existe."
            )
            continue
        if not target.flag_ative:
            errors.append(
                f"Node SubWorkflow '{node_id}' aponta para workflow '{wh}' "
                "que esta desativado."
            )
            continue

        try:
            target_def = decrypt_workflow_connections(target.definition or {})
        except Exception:
            target_def = target.definition or {}

        contract = extract_contract(target_def)

        # Só SubWorkflowOutput é obrigatório — define o valor de retorno.
        # SubWorkflowInput é opcional (sub-fluxo pode não receber nada) e
        # `ports` vazio significa passthrough, não ausência de contrato.
        if not contract.get("has_output_node"):
            errors.append(
                f"Node SubWorkflow '{node_id}' aponta para workflow '{wh}' "
                "sem node SubWorkflowOutput: não há saída declarada para consumir."
            )
            continue

        if contract.get("output_node_count", 0) > 1:
            errors.append(
                f"Node SubWorkflow '{node_id}' aponta para workflow '{wh}' com "
                f"{contract['output_node_count']} nodes SubWorkflowOutput. "
                "Apenas um é permitido."
            )
            continue

        # Pai envia mapeamento para filho que não tem entry point: os dados
        # seriam silenciosamente ignorados em runtime.
        if ref["inputs_mapping"] and not contract.get("has_input_node"):
            errors.append(
                f"Node SubWorkflow '{node_id}' mapeia entradas para o workflow "
                f"'{wh}', que não tem SubWorkflowInput. Os dados não chegariam "
                "ao sub-fluxo — adicione o node de entrada ou remova o mapeamento."
            )
            continue

        # Valida inputsMapping contra contrato
        mapping_errors = validate_inputs_mapping(ref["inputs_mapping"], contract)
        for msg in mapping_errors:
            errors.append(f"Node SubWorkflow '{node_id}' -> workflow '{wh}': {msg}")

    return errors
