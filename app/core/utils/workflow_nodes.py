# app/core/utils/workflow_nodes.py
"""Reading the properties of a definition node.

Lives in `core/utils` — and not inside a service — because three independent
paths need to agree on the extraction: the dispatch (which validates and
injects credentials), the move's impact report and any future collector. While
the function was private to `workflow_execution_service`, the report imported
it with the underscore, tying one service to another's internals.
"""


def node_props(node: dict) -> dict:
    """Extracts the node's effective properties dict.

    Uses the same fallback chain as the frontend/worker: `data.properties` takes
    precedence over `properties`. Centralized so that collector and validator
    agree on which node field contains `credential_id` — prevents an attacker
    from bypassing validation by forging a `data.properties` without
    `credential_id` alongside a real `properties.credential_id`.
    """
    return node.get("data", {}).get("properties") or node.get("properties") or {}
