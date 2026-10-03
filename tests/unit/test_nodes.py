# tests/unit/test_nodes.py
"""Unit tests for the flow engine nodes."""
import pytest
try:
    from flow.registry import NODE_REGISTRY as _NODE_REGISTRY  # noqa: F401
    _FLOW_AVAILABLE = True
except ImportError:
    _FLOW_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _FLOW_AVAILABLE, reason="Dependencias do flow nao disponiveis")


class TestNodeRegistry:

    def test_registry_not_empty(self):
        """O registry deve conter nodes registrados."""
        from flow.registry import NODE_REGISTRY
        assert len(NODE_REGISTRY) > 0

    def test_registry_has_core_nodes(self):
        """Must contain the essential nodes."""
        from flow.registry import NODE_REGISTRY
        expected = ["HttpRequest", "Buffer", "Merge", "Conditional", "DataOutput", "DataInput", "WFS"]
        for name in expected:
            assert name in NODE_REGISTRY, f"Node '{name}' nao encontrado no registry"

    def test_all_nodes_have_description(self):
        """Every node must have a valid description()."""
        from flow.registry import NODE_REGISTRY
        for name, node_cls in NODE_REGISTRY.items():
            desc = node_cls.description()
            assert isinstance(desc, dict), f"Node '{name}' description() nao retorna dict"
            assert "name" in desc, f"Node '{name}' description() sem 'name'"
            assert "type" in desc, f"Node '{name}' description() sem 'type'"

    def test_all_nodes_have_valid_type(self):
        """Every node must have a valid type."""
        from flow.registry import NODE_REGISTRY
        valid_types = {"datasource", "action", "spatial", "output", "control", "trigger"}
        for name, node_cls in NODE_REGISTRY.items():
            desc = node_cls.description()
            assert desc["type"] in valid_types, \
                f"Node '{name}' tem type invalido: '{desc['type']}'"


class TestNodeFactory:

    def test_create_known_node(self):
        """Must create an instance of a known node."""
        from flow.factory import NodeFactory
        factory = NodeFactory()
        node = factory.create({"id": "node-1", "name": "Buffer", "properties": {}})
        assert node is not None
        assert node.node_id == "node-1"

    def test_create_unknown_node_raises(self):
        """Must raise an error for an unknown node."""
        from flow.factory import NodeFactory
        factory = NodeFactory()
        with pytest.raises((ValueError, KeyError)):
            factory.create({"id": "node-1", "name": "NaoExiste", "properties": {}})


class TestDatasetScanner:
    """Tests for the GeoSync dataset scanner."""

    def test_supported_extensions(self):
        """Must include common geospatial extensions."""
        from executor.sync.scanner import SUPPORTED_EXTENSIONS
        for ext in [".geojson", ".shp", ".gpkg", ".tiff", ".csv", ".kml"]:
            assert ext in SUPPORTED_EXTENSIONS, f"Extensao '{ext}' nao suportada"

    def test_ignore_names(self):
        """Must include system files in the ignore list."""
        from executor.sync.scanner import _IGNORE_NAMES
        assert ".atlans-sync.json" in _IGNORE_NAMES
        assert ".DS_Store" in _IGNORE_NAMES
        assert "Thumbs.db" in _IGNORE_NAMES


class TestBufferNode:

    @pytest.mark.asyncio
    async def test_buffer_description(self):
        """Buffer node deve ter properties corretas."""
        pytest.importorskip("geopandas")
        from flow.nodes.spatial.buffer import BufferNode
        desc = BufferNode.description()
        assert desc["name"] == "Buffer"
        assert desc["type"] == "spatial"
        prop_names = [p["name"] for p in desc.get("properties", [])]
        assert "distance" in prop_names
        assert "distanceUnit" in prop_names


class TestMergeNode:

    @pytest.mark.asyncio
    async def test_merge_description(self):
        """Merge node deve aceitar multiplos inputs."""
        pytest.importorskip("geopandas")
        from flow.nodes.control.merge import MergeNode
        desc = MergeNode.description()
        assert desc["name"] == "Merge"
        assert desc["type"] == "control"
