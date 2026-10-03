"""Utilities to detect trigger types in workflow definitions.

The `trigger_workflow_inline` function was removed along with the
TriggerWorkflow node — sub-workflows are now executed exclusively by
SubWorkflow (control category), which has a resolver injected by the executor
and does not depend on `app.*` at runtime.
"""


def has_webhook_trigger(definition: dict) -> bool:
    """True if the definition contains at least one WebhookTrigger node.

    Used by endpoints that must only execute workflows configured for
    that trigger type (e.g., POST /webhook/execute/{id_hash}).

    Follows the same pattern as `extract_schedule_node` in app.core.scheduling.hooks
    (checks type + name).
    """
    for node in definition.get("nodes", []):
        if node.get("type") == "trigger" and node.get("name") == "WebhookTrigger":
            return True
    return False
