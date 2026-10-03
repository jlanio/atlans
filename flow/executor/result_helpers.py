# flow/executor/result_helpers.py
"""Shared functions for collecting artifacts and responses from the executor's outputs."""
from typing import Any, Dict, List, Optional


def collect_artifacts(final_outputs: Dict[str, Any]) -> Dict[str, List[dict]]:
    """Collects __artifact__ metadata from each node's outputs."""
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
    """Collects the first __subworkflow_output__ — the child workflow's public API.

    Used by SubWorkflowNode to expose named outputs to the calling workflow
    instead of the raw final_outputs dict of UUIDs. Returns None when the
    child's SubWorkflowOutput did not run in this round; the caller treats that
    as an error (the sub-workflow contract already requires the node).
    """
    for outputs in (final_outputs or {}).values():
        if isinstance(outputs, dict) and "__subworkflow_output__" in outputs:
            return outputs["__subworkflow_output__"]
    return None
