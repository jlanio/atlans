# tests/unit/test_divida_higiene_borda.py
"""Edge hygiene: what accepted what it should not, or hid what it should say.

Items recorded as pending in PRs #96 and #97. None changes the behavior for
whoever already uses the API correctly — they change what happens with
malformed input, with the missing role and with the silent failure.

(Item #99.4 — `UploadUrlRequest` of `POST /drive/upload-url` — left together
with the route, removed in F1 of the simplification for having no consumer.)
"""
import pytest
from pydantic import ValidationError

from app.schemas.workflow import WorkflowDuplicate, WorkflowMove


# ── #96.5: WorkflowDuplicate without extra="forbid" ──────────────────────────


class TestWorkflowDuplicate:

    def test_optional_name_stays_optional(self):
        assert WorkflowDuplicate().name is None
        assert WorkflowDuplicate(name="Cópia").name == "Cópia"

    def test_unknown_field_is_rejected(self):
        """`workspace_id` was silently discarded — and the copy stays in the same
        workspace as the original, so whoever sent it thought it had moved."""
        with pytest.raises(ValidationError):
            WorkflowDuplicate(name="Cópia", workspace_id="ws-outro")

    def test_aligned_with_sibling_WorkflowMove(self):
        """The sibling was already strict; it was the divergence that was recorded."""
        assert WorkflowDuplicate.model_config.get("extra") == "forbid"
        assert WorkflowMove.model_config.get("extra") == "forbid"


# ── #97.3: GET /pins was the only one of the three pin routes without a role ──


def test_the_list_pins_route_requires_a_role():
    """The sibling `PUT`/`DELETE` require `editor`; this one required nothing.

    And the MCP tool `list_pins` already required `viewer` (`app/mcp/guardas.py`),
    so the SAME read answered by two yardsticks depending on the entry point.

    The role is declared in the route's dependency (`workflow_com_papel`), and it
    is that declaration that is pinned here — read from the registered route,
    without building the app. The 403 for each role below the minimum is
    exercised by the matrix in `test_papel_minimo_das_rotas.py`.
    """
    from app.api.routers import workflows_router

    (rota,) = [
        r for r in workflows_router.router.routes
        if r.path == "/workflows/{id_hash}/pins" and "GET" in r.methods
    ]
    stored_blocks = [
        d.call.papel_minimo for d in rota.dependant.dependencies
        if hasattr(d.call, "papel_minimo")
    ]
    assert stored_blocks == ["viewer"], "sem o papel declarado não há o que checar"


def test_the_route_rule_is_the_same_as_the_tool():
    """Diverging here is the original defect, not a choice."""
    from app.mcp.guardas import GUARDAS

    assert GUARDAS["list_pins"].papel == "viewer"


# ── #96.2: the copy was born without an owner ────────────────────────────────


def test_duplicate_requires_the_copier_as_author():
    """`duplicated_by` exists so that REST stops creating orphan workflows.

    The MCP tool already stamped it by hand; now both entry points use the same
    parameter, and the stamp lives in a single place. It was optional "for an
    internal caller without a user" — which never existed —, and without it the
    copy also skipped the credentials guard (SEG-12). It is now required; the
    rule for the four writes is in test_workflow_credencial_guard.py.
    """
    import inspect

    from app.services.workflow_service import WorkflowService

    parametro = inspect.signature(WorkflowService.duplicate_workflow).parameters["duplicated_by"]
    assert parametro.kind is inspect.Parameter.KEYWORD_ONLY
    assert parametro.default is inspect.Parameter.empty


# ── #96.4: restore_version engolia falha de agendamento ──────────────────────


def test_restore_version_returns_the_schedule_warnings():
    """Without this, restoring a version with a broken cron looked like success.

    The symptom of a schedule that did not sync is SILENCE: nothing fails, the
    routine just stops happening. `update_workflow` already returned
    `schedule_notices`; `restore_version` did not.
    """
    import inspect

    from app.services import workflow_version_service

    fonte = inspect.getsource(workflow_version_service.restore_version)
    assert "schedule_notices" in fonte
    assert "wf.schedule_notices" in fonte, "o atributo transiente precisa chegar ao objeto"
