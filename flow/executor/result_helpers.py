# flow/executor/result_helpers.py
"""Funções compartilhadas para coleta de artefatos e respostas dos outputs do executor."""
from typing import Any, Dict, List, Optional


def collect_artifacts(final_outputs: Dict[str, Any]) -> Dict[str, List[dict]]:
    """Coleta metadados __artifact__ dos outputs de cada nó."""
    artifacts: Dict[str, List[dict]] = {}
    for node_id, outputs in (final_outputs or {}).items():
        if isinstance(outputs, dict) and "__artifact__" in outputs:
            artifacts.setdefault(node_id, []).append(outputs["__artifact__"])
    return artifacts


def collect_response(final_outputs: Dict[str, Any]) -> Optional[dict]:
    """Coleta o primeiro __response__ encontrado nos outputs (ResponseNode)."""
    for outputs in (final_outputs or {}).values():
        if isinstance(outputs, dict) and "__response__" in outputs:
            return outputs["__response__"]
    return None


def collect_subworkflow_output(final_outputs: Dict[str, Any]) -> Optional[dict]:
    """Coleta o primeiro __subworkflow_output__ — API publica do workflow filho.

    Usado pelo SubWorkflowNode para expor outputs nomeados ao workflow chamador
    em vez do dict de UUIDs do final_outputs cru. Retorna None quando o
    SubWorkflowOutput do filho nao executou nesta rodada; o caller trata isso
    como erro (o contrato do sub-fluxo ja exige o node).
    """
    for outputs in (final_outputs or {}).values():
        if isinstance(outputs, dict) and "__subworkflow_output__" in outputs:
            return outputs["__subworkflow_output__"]
    return None
