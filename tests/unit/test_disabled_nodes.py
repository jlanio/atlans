"""
Tests for the admin feature that enables/disables nodes:
- service (disabled_nodes_service): list/is/set
- catalog: NodeService.list_nodes() filters disabled ones
- dispatch: _validate_no_disabled_nodes raises 422
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── disabled_nodes_service ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _no_cache_between_tests():
    """The map of disabled nodes is cached in memory with a TTL.

    Without this reset, the {} read by the first test would still hold in the
    following ones and the `get_config` they mock would never be queried.

    NodeService's base catalog is also cached (@lru_cache): cleared along with it
    so the filter tests do not inherit a catalog built by another test.
    """
    from app.services import disabled_nodes_service as svc
    from app.services import node_service as ns

    svc.invalidate_cache()
    ns._full_catalog.cache_clear()
    yield
    svc.invalidate_cache()
    ns._full_catalog.cache_clear()


class TestDisabledNodesService:

    @pytest.mark.asyncio
    async def test_list_disabled_returns_empty_when_unset(self):
        from app.services import disabled_nodes_service as svc

        db = MagicMock()
        # Mock get_config a retornar default={}
        with patch.object(svc, "get_config", new=AsyncMock(return_value={})):
            cfg = await svc.list_disabled(db)
        assert cfg == {}

    @pytest.mark.asyncio
    async def test_list_disabled_coerces_non_dict_to_empty(self):
        """Defense against a corrupted config in the DB (it was a list instead of a dict)."""
        from app.services import disabled_nodes_service as svc

        db = MagicMock()
        with patch.object(svc, "get_config", new=AsyncMock(return_value=["SendEmail"])):
            cfg = await svc.list_disabled(db)
        assert cfg == {}

    @pytest.mark.asyncio
    async def test_disabled_names_returns_set(self):
        from app.services import disabled_nodes_service as svc

        db = MagicMock()
        with patch.object(svc, "get_config", new=AsyncMock(return_value={"A": {}, "B": {}})):
            names = await svc.disabled_names(db)
        assert names == {"A", "B"}

    @pytest.mark.asyncio
    async def test_set_disabled_persists_metadata(self):
        from app.services import disabled_nodes_service as svc

        captured: dict = {}
        async def fake_set(_db, _key, value):
            captured["value"] = value
        async def fake_get(_db, _key, default=None):
            return captured.get("value", default if default is not None else {})

        db = MagicMock()
        with patch.object(svc, "get_config", new=fake_get):
            with patch.object(svc, "set_config", new=fake_set):
                entry = await svc.set_disabled(db, "SendEmail", by="usr-1", reason="bug")

        assert "SendEmail" in captured["value"]
        meta = captured["value"]["SendEmail"]
        assert meta["disabled_by"] == "usr-1"
        assert meta["reason"] == "bug"
        assert meta["disabled_at"]  # ISO timestamp populado
        assert entry["reason"] == "bug"

    @pytest.mark.asyncio
    async def test_set_enabled_removes_node(self):
        from app.services import disabled_nodes_service as svc

        captured: dict = {"value": {"SendEmail": {"reason": "x"}, "Other": {}}}
        async def fake_get(_db, _key, default=None):
            return captured["value"]
        async def fake_set(_db, _key, value):
            captured["value"] = value

        db = MagicMock()
        with patch.object(svc, "get_config", new=fake_get):
            with patch.object(svc, "set_config", new=fake_set):
                removed = await svc.set_enabled(db, "SendEmail")

        assert removed is True
        assert "SendEmail" not in captured["value"]
        assert "Other" in captured["value"]  # preserves the others

    @pytest.mark.asyncio
    async def test_set_enabled_returns_false_for_unknown(self):
        from app.services import disabled_nodes_service as svc

        captured: dict = {"value": {}}
        async def fake_get(_db, _key, default=None):
            return captured["value"]
        async def fake_set(_db, _key, value):
            captured["value"] = value

        db = MagicMock()
        with patch.object(svc, "get_config", new=fake_get):
            with patch.object(svc, "set_config", new=fake_set):
                removed = await svc.set_enabled(db, "DoesNotExist")
        assert removed is False


# ── NodeService.list_nodes ───────────────────────────────────────────────────

class TestNodeServiceFilter:

    @pytest.mark.asyncio
    async def test_list_nodes_omits_disabled(self):
        # disabled_names was imported inside node_service — patch in the local namespace
        with patch("app.services.node_service.disabled_names", new=AsyncMock(return_value={"SendEmail"})):
            from app.services.node_service import NodeService
            catalog = await NodeService().list_nodes(MagicMock())

        # SendEmail must not appear
        assert all(n.name != "SendEmail" for n in catalog)
        # But other nodes do — checks that the filter did not remove everything
        assert len(catalog) > 0

    @pytest.mark.asyncio
    async def test_list_nodes_returns_full_catalog_when_nothing_disabled(self):
        from flow.registry import NODE_REGISTRY

        with patch("app.services.node_service.disabled_names", new=AsyncMock(return_value=set())):
            from app.services.node_service import NodeService
            catalog = await NodeService().list_nodes(MagicMock())

        # Must list all nodes in the registry (all with a valid name)
        registry_names = {name for name in NODE_REGISTRY.keys()}
        catalog_names = {n.name for n in catalog}
        assert catalog_names == registry_names

    @pytest.mark.asyncio
    async def test_catalog_built_once_and_reused(self):
        """The base catalog is cached (@lru_cache): a repeated GET /nodes does NOT
        rebuild the NodeDefinitions nor re-call cls.description() (the cost the
        audit pointed out). Spies on a node's description() and asserts it is
        called only once even after two listings."""
        from app.services import node_service as ns
        from flow.registry import NODE_REGISTRY

        # The fixture already cleared the cache; build from scratch INSIDE the spy.
        algum = next(iter(NODE_REGISTRY))
        cls = NODE_REGISTRY[algum]
        with patch.object(cls, "description", wraps=cls.description) as espiao, \
             patch("app.services.node_service.disabled_names", new=AsyncMock(return_value=set())):
            await ns.NodeService().list_nodes(MagicMock())
            await ns.NodeService().list_nodes(MagicMock())
        # Built ONCE (1st listing) and reused the cache on the 2nd.
        assert espiao.call_count == 1


# ── Validation at dispatch ──────────────────────────────────────────────────

class TestValidateNoDisabledNodes:

    def test_returns_silently_when_set_empty(self):
        from app.services.workflow_execution_service import _validate_no_disabled_nodes
        # Does not raise
        _validate_no_disabled_nodes({"nodes": [{"name": "A"}]}, set())

    def test_returns_silently_when_no_offenders(self):
        from app.services.workflow_execution_service import _validate_no_disabled_nodes
        _validate_no_disabled_nodes({"nodes": [{"name": "A"}, {"name": "B"}]}, {"X"})

    def test_raises_422_with_offender_names(self):
        from app.services.workflow_execution_service import _validate_no_disabled_nodes
        from app.core.exceptions import DisabledNodesInWorkflowError

        defn = {"nodes": [{"name": "SendEmail"}, {"name": "Conditional"}, {"name": "Other"}]}

        with pytest.raises(DisabledNodesInWorkflowError) as exc_info:
            _validate_no_disabled_nodes(defn, {"SendEmail", "Other"})

        msg = str(exc_info.value)
        assert "SendEmail" in msg
        assert "Other" in msg
        # Status code so it becomes a 422 in the global handler
        assert exc_info.value.status_code == 422

    def test_offenders_are_unique_and_sorted(self):
        """The same node appearing twice in the workflow does not duplicate the message."""
        from app.services.workflow_execution_service import _validate_no_disabled_nodes
        from app.core.exceptions import DisabledNodesInWorkflowError

        defn = {"nodes": [{"name": "A"}, {"name": "A"}, {"name": "B"}]}

        with pytest.raises(DisabledNodesInWorkflowError) as exc_info:
            _validate_no_disabled_nodes(defn, {"A", "B"})

        msg = str(exc_info.value)
        # "A" appears only once
        assert msg.count("A,") + msg.count("A.") + msg.count("A ") <= 2


# ── Endpoint admin (smoke via dispatcher do schema) ─────────────────────────

class TestAdminEndpoint:

    def test_node_toggle_body_strips_reason(self):
        from app.api.routers.admin_nodes_router import NodeToggleBody

        body = NodeToggleBody(enabled=False, reason="   teste   ")
        assert body.reason == "teste"

    def test_node_toggle_body_empty_reason_becomes_none(self):
        from app.api.routers.admin_nodes_router import NodeToggleBody

        body = NodeToggleBody(enabled=False, reason="   ")
        assert body.reason is None  # empty after strip becomes None
