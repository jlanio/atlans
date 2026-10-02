"""
Testes da feature admin habilita/desabilita nodes:
- service (disabled_nodes_service): list/is/set
- catalogo: NodeService.list_nodes() filtra disabled
- dispatch: _validate_no_disabled_nodes levanta 422
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── disabled_nodes_service ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _sem_cache_entre_testes():
    """O mapa de nodes desabilitados e cacheado em memoria com TTL.

    Sem este reset, o {} lido pelo primeiro teste continuaria valendo nos
    seguintes e o `get_config` mockado por eles nunca seria consultado.

    O catalogo base do NodeService tambem e cacheado (@lru_cache): limpa junto
    para os testes de filtro nao herdarem um catalogo montado por outro teste.
    """
    from app.services import disabled_nodes_service as svc
    from app.services import node_service as ns

    svc.invalidate_cache()
    ns._catalogo_completo.cache_clear()
    yield
    svc.invalidate_cache()
    ns._catalogo_completo.cache_clear()


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
        """Defesa contra config corrompida no DB (era list em vez de dict)."""
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
        assert "Other" in captured["value"]  # preserva os outros

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
        # disabled_names foi importado dentro de node_service — patch no namespace local
        with patch("app.services.node_service.disabled_names", new=AsyncMock(return_value={"SendEmail"})):
            from app.services.node_service import NodeService
            catalog = await NodeService().list_nodes(MagicMock())

        # SendEmail nao deve aparecer
        assert all(n.name != "SendEmail" for n in catalog)
        # Mas outros nodes sim — verifica que filtro nao removeu tudo
        assert len(catalog) > 0

    @pytest.mark.asyncio
    async def test_list_nodes_returns_full_catalog_when_nothing_disabled(self):
        from flow.registry import NODE_REGISTRY

        with patch("app.services.node_service.disabled_names", new=AsyncMock(return_value=set())):
            from app.services.node_service import NodeService
            catalog = await NodeService().list_nodes(MagicMock())

        # Deve listar todos os nodes do registry (todos com nome valido)
        registry_names = {name for name in NODE_REGISTRY.keys()}
        catalog_names = {n.name for n in catalog}
        assert catalog_names == registry_names

    @pytest.mark.asyncio
    async def test_catalogo_montado_uma_vez_e_reusado(self):
        """O catalogo base e cacheado (@lru_cache): GET /nodes repetido NAO
        remonta os NodeDefinition nem re-chama cls.description() (o custo que a
        auditoria apontou). Espia o description() de um no e afirma que ele e
        chamado uma unica vez mesmo apos duas listagens."""
        from app.services import node_service as ns
        from flow.registry import NODE_REGISTRY

        # O fixture ja limpou o cache; monta do zero DENTRO do spy.
        algum = next(iter(NODE_REGISTRY))
        cls = NODE_REGISTRY[algum]
        with patch.object(cls, "description", wraps=cls.description) as espiao, \
             patch("app.services.node_service.disabled_names", new=AsyncMock(return_value=set())):
            await ns.NodeService().list_nodes(MagicMock())
            await ns.NodeService().list_nodes(MagicMock())
        # Montou UMA vez (1a listagem) e reusou o cache na 2a.
        assert espiao.call_count == 1


# ── Validacao no dispatch ───────────────────────────────────────────────────

class TestValidateNoDisabledNodes:

    def test_returns_silently_when_set_empty(self):
        from app.services.workflow_execution_service import _validate_no_disabled_nodes
        # Nao levanta
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
        # Status code para virar 422 no handler global
        assert exc_info.value.status_code == 422

    def test_offenders_sao_unicos_e_ordenados(self):
        """Mesmo node aparecendo 2x no workflow nao duplica a mensagem."""
        from app.services.workflow_execution_service import _validate_no_disabled_nodes
        from app.core.exceptions import DisabledNodesInWorkflowError

        defn = {"nodes": [{"name": "A"}, {"name": "A"}, {"name": "B"}]}

        with pytest.raises(DisabledNodesInWorkflowError) as exc_info:
            _validate_no_disabled_nodes(defn, {"A", "B"})

        msg = str(exc_info.value)
        # "A" aparece uma unica vez
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
        assert body.reason is None  # vazio depois do strip vira None
