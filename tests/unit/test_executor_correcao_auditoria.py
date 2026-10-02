"""Regressao das 4 correcoes do motor (auditoria: fluxo/correcao).

Cada teste falha SEM o fix; a docstring nomeia a mutacao que derruba SO ele.
Duas correcoes sao MUDANCA DE COMPORTAMENTO (gather cancela irmaos; retry so em
erro transitorio) e estao marcadas como tal.
"""
import asyncio

import geopandas as gpd
import pytest
from shapely.geometry import Point
from unittest.mock import MagicMock

from flow.nodes.base import BaseNode
from flow.executor.core import WorkflowExecutor
from flow.executor.spill import _load_from_disk


def _publisher():
    pub = MagicMock()
    pub.publish_event = MagicMock()
    return pub


def _gdf():
    return gpd.GeoDataFrame({"n": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")


# Estado observavel dos nos de efeito colateral e de contagem de tentativas.
EFEITOS: list = []
CHAMADAS: dict = {}


class _Ramo(BaseNode):
    """Nó de controle que emite branch=False (o ramo True não é tomado)."""
    @classmethod
    def description(cls):
        return {"name": "TesteRamo", "type": "control", "properties": []}

    async def execute(self, inputs):
        return {"output": inputs.get("output"), "branch": False}


class _Fonte(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "TesteFonte", "type": "action", "properties": []}

    async def execute(self, inputs):
        return {"output": _gdf()}


class _Coletor(BaseNode):
    """Merge que reporta as CHAVES que recebeu — é como vemos o vazamento."""
    @classmethod
    def description(cls):
        return {"name": "TesteColetor", "type": "control", "properties": []}

    async def execute(self, inputs):
        return {"chaves": sorted(inputs.keys())}


class _FalhaRapida(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "TesteFalhaRapida", "type": "action", "properties": []}

    async def execute(self, inputs):
        raise RuntimeError("falhei rapido")


class _EfeitoLento(BaseNode):
    """Roda ~0,2 s e SÓ ENTÃO commita o efeito — simula computar e depois gravar."""
    @classmethod
    def description(cls):
        return {"name": "TesteEfeitoLento", "type": "action", "properties": []}

    async def execute(self, inputs):
        await asyncio.sleep(0.2)
        EFEITOS.append("Y")  # o "commit" que não deve acontecer se cancelado
        return {"output": None}


class _FalhaClassificada(BaseNode):
    """Levanta ValueError (nao-retentavel) ou ConnectionError (transitorio),
    conforme o parametro `tipo`, contando as tentativas."""
    @classmethod
    def description(cls):
        return {"name": "TesteFalhaClassificada", "type": "action", "properties": []}

    async def execute(self, inputs):
        CHAMADAS[self.node_id] = CHAMADAS.get(self.node_id, 0) + 1
        if self.get_param("tipo", "user") == "transient":
            raise ConnectionError("rede caiu")
        raise ValueError("dado ruim")


@pytest.fixture
def _registra():
    from flow.registry import NODE_REGISTRY
    novos = {
        "TesteRamo": _Ramo, "TesteFonte": _Fonte, "TesteColetor": _Coletor,
        "TesteFalhaRapida": _FalhaRapida, "TesteEfeitoLento": _EfeitoLento,
        "TesteFalhaClassificada": _FalhaClassificada,
    }
    NODE_REGISTRY.update(novos)
    EFEITOS.clear(); CHAMADAS.clear()
    try:
        yield
    finally:
        for n in novos:
            NODE_REGISTRY.pop(n, None)


def _trigger(nid):
    return {"id": nid, "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}}


# ── F-audit: aresta de ramo NAO tomado nao injeta no merge sobrevivente ──────

def test_aresta_de_ramo_desativado_nao_injeta_no_merge(_registra):
    """Mutacao: remover a checagem `id(edge) in self._deactivated_edge_ids` na
    montagem de inputs.

    Ramo emite branch=False → a aresta Ramo→C(True) é desativada; mas C tem
    outra aresta VIVA (Fonte→C), então C RODA (has_live_input). Sem o fix, a
    montagem itera TODAS as arestas de C e, como Ramo está 'completed' (não
    'skipped'), injeta a saída do ramo REJEITADO — a chave 'branch' vaza para C.
    """
    definition = {
        "nodes": [_trigger("T"),
                  {"id": "Fonte", "type": "action", "name": "TesteFonte", "properties": {}},
                  {"id": "Ramo", "type": "control", "name": "TesteRamo", "properties": {}},
                  {"id": "C", "type": "control", "name": "TesteColetor", "properties": {}}],
        "edges": [
            {"source": "T", "target": "Fonte"},
            {"source": "T", "target": "Ramo"},
            {"source": "Fonte", "target": "C"},               # aresta de dado
            {"source": "Ramo", "target": "C", "condition": True},  # ramo NÃO tomado
        ],
    }
    ex = WorkflowExecutor(definition, task_id="fa", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert ex.node_stats["C"]["status"] != "skipped", "C tem dado vivo de Fonte: roda"
    assert "branch" not in final["C"]["chaves"], "o ramo rejeitado NÃO pode injetar em C"
    assert "output" in final["C"]["chaves"], "o dado de Fonte deve chegar"


# ── F-audit: gather cancela os irmaos na 1a falha (MUDANCA DE COMPORTAMENTO) ──

async def test_gather_cancela_irmaos_na_primeira_falha(_registra):
    """Mutacao: voltar a `results = await asyncio.gather(*tasks)` sem cancelar.

    X falha rápido; Y computa ~0,2 s e SÓ ENTÃO commita o efeito. Com o fix, a
    falha de X cancela Y antes do commit. Sem o fix, Y segue vivo (gather não
    cancela) e commita durante a espera abaixo.
    """
    definition = {
        "nodes": [_trigger("T"),
                  {"id": "X", "type": "action", "name": "TesteFalhaRapida", "properties": {}},
                  {"id": "Y", "type": "action", "name": "TesteEfeitoLento", "properties": {}}],
        "edges": [{"source": "T", "target": "X"}, {"source": "T", "target": "Y"}],
    }
    ex = WorkflowExecutor(definition, task_id="ga", publisher=_publisher())
    with pytest.raises(Exception):
        await ex.run(initial_inputs={"T": {"output": _gdf()}})
    await asyncio.sleep(0.5)  # dá tempo de Y commitar SE não tiver sido cancelado
    assert EFEITOS == [], "o irmão não pode commitar efeito após a falha do batch"


# ── F-audit: retry so em erro transitorio (MUDANCA DE COMPORTAMENTO) ─────────

def test_retry_nao_retenta_erro_deterministico(_registra):
    """Mutacao: remover o gate `is_retryable(classify_error(...))`.

    ValueError é 'user' (não-retentável): execute deve rodar UMA vez, não 3.
    """
    definition = {
        "nodes": [_trigger("T"),
                  {"id": "R", "type": "action", "name": "TesteFalhaClassificada",
                   "properties": {"tipo": "user", "retry_count": 2, "retry_delay_s": 0}}],
        "edges": [{"source": "T", "target": "R"}],
    }
    ex = WorkflowExecutor(definition, task_id="rt1", publisher=_publisher())
    with pytest.raises(Exception):
        asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert CHAMADAS.get("R") == 1, "erro determinístico não pode ser retentado"


def test_retry_retenta_erro_transitorio(_registra):
    """ConnectionError é 'transient': execute roda 1 + 2 retries = 3 vezes."""
    definition = {
        "nodes": [_trigger("T"),
                  {"id": "R", "type": "action", "name": "TesteFalhaClassificada",
                   "properties": {"tipo": "transient", "retry_count": 2, "retry_delay_s": 0}}],
        "edges": [{"source": "T", "target": "R"}],
    }
    ex = WorkflowExecutor(definition, task_id="rt2", publisher=_publisher())
    with pytest.raises(Exception):
        asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert CHAMADAS.get("R") == 3, "erro transitório deve ser retentado até esgotar"


# ── F-audit: spill que nao restaura falha alto, nao entrega a sentinela ──────

def test_spill_nao_restaurado_levanta(tmp_path):
    """Mutacao: voltar a só logar o warning e deixar a referência sentinela.

    Sem o fix, o nó consumidor receberia {'__spilled__': True, ...} como se fosse
    dado. Agora falha alto com a causa real.
    """
    outputs = {"gdf": {"__spilled__": True, "__spill_path__": str(tmp_path / "nao_existe.parquet")}}
    with pytest.raises(RuntimeError):
        _load_from_disk(outputs)
