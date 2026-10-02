import asyncio
import os
import geopandas as gpd
import pandas as pd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import reject_unsupported_geom_types
from flow.utils.logger import get_logger

logger = get_logger(__name__)

# ── Controle de memória do overlay ────────────────────────────────────────────
# O gpd.overlay materializa o índice de pares candidatos INTEIRO
# (df2.sindex.query sobre TODA a df1) antes de calcular qualquer interseção. Para
# camadas grandes/densas isso estoura a RAM — ex.: 747M pares = ~11 GiB só no
# array de índices (2 × 747M × 8 bytes), antes mesmo do cálculo geométrico.
#
# Estratégia: estimar o fanout médio (candidatos por feição de A) por amostragem
# barata do sindex de B e fatiar A em blocos dimensionados para manter os pares
# por bloco perto de _TARGET_PAIRS_PER_CHUNK. O sindex de B é construído uma vez
# (cached_property) e reusado em todos os blocos. O resultado é idêntico ao
# overlay direto — particionar linhas de A não altera os pares A∩B.
_TARGET_PAIRS_PER_CHUNK = max(1, int(os.getenv("INTERSECTION_TARGET_PAIRS", str(20_000_000))))
_MAX_CHUNK_ROWS = max(1, int(os.getenv("INTERSECTION_MAX_CHUNK_ROWS", "50000")))
_FANOUT_SAMPLE = max(1, int(os.getenv("INTERSECTION_FANOUT_SAMPLE", "256")))


def _clean_layer(gdf: gpd.GeoDataFrame, name: str) -> gpd.GeoDataFrame:
    """Remove geometrias nulas/vazias (não intersectam nada e quebram o sindex)
    e avisa sobre geometrias inválidas (bbox degenerada infla o fanout)."""
    geom = gdf.geometry
    bad = geom.isna() | geom.is_empty
    n_bad = int(bad.sum())
    if n_bad:
        logger.warning("Interseção: removendo %d geometria(s) nula(s)/vazia(s) da camada %s.", n_bad, name)
        gdf = gdf.loc[~bad]

    if len(gdf):
        n_invalid = int((~gdf.geometry.is_valid).sum())
        if n_invalid:
            logger.warning(
                "Interseção: %d geometria(s) inválida(s) na camada %s — podem inflar o uso de "
                "memória e produzir resultados incorretos. Considere um nó de validação/correção "
                "de geometria (make_valid) antes desta operação.",
                n_invalid, name,
            )
    return gdf


def _estimate_avg_fanout(srcA: gpd.GeoDataFrame, srcB: gpd.GeoDataFrame) -> float:
    """Estima candidatos (bbox-overlap) por feição de A amostrando o sindex de B.

    Barato: O(_FANOUT_SAMPLE) consultas. Também aquece srcB.sindex, reusado pelo
    overlay. Amostra por passo determinístico (sem aleatoriedade)."""
    n = len(srcA)
    step = max(1, n // _FANOUT_SAMPLE)
    geoms = srcA.geometry
    total = 0
    count = 0
    for i in range(0, n, step):
        total += len(srcB.sindex.query(geoms.iloc[i]))
        count += 1
    return (total / count) if count else 0.0


def _overlay_intersection_bounded(srcA: gpd.GeoDataFrame, srcB: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """gpd.overlay(how='intersection') com pico de memória limitado via blocos
    adaptativos dimensionados pelo fanout estimado."""
    n = len(srcA)
    avg_fanout = _estimate_avg_fanout(srcA, srcB)
    est_total = int(avg_fanout * n)
    logger.info(
        "Interseção: ~%.1f candidato(s)/feição em A → estimado ~%d par(es) totais.",
        avg_fanout, est_total,
    )

    if avg_fanout <= 0:
        # Nenhum candidato (extents disjuntos) — overlay direto resolve barato.
        chunk = n
    else:
        chunk = max(1, min(_MAX_CHUNK_ROWS, int(_TARGET_PAIRS_PER_CHUNK / avg_fanout)))

    if chunk >= n:
        return gpd.overlay(srcA, srcB, how="intersection")

    n_chunks = (n + chunk - 1) // chunk
    logger.info(
        "Interseção em %d bloco(s) de %d feição(ões) de A (alvo ~%d pares/bloco, limita pico de RAM).",
        n_chunks, chunk, _TARGET_PAIRS_PER_CHUNK,
    )
    parts: list[gpd.GeoDataFrame] = []
    for start in range(0, n, chunk):
        part = gpd.overlay(srcA.iloc[start:start + chunk], srcB, how="intersection")
        if len(part):
            parts.append(part)

    if not parts:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=srcA.crs)
    return gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=srcA.crs)


@register_node
class IntersectionNode(BaseNode):
    """
    Executa a interseção entre duas camadas (GeoDataFrames) e retorna as feições resultantes.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'IntersectionNode',
            'alias': 'Interseção',
            'description': 'Realiza a operação de interseção entre duas camadas vetoriais.',
            'type': 'spatial',
            'properties': [],
            'inputs': [
                {'name': 'layerA', 'type': 'geodataframe', 'description': 'Primeira camada (GeoDataFrame).'},
                {'name': 'layerB', 'type': 'geodataframe', 'description': 'Segunda camada (GeoDataFrame).'}
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame resultante da interseção entre as duas camadas'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, gpd.GeoDataFrame]:
        self.validate()
        # Obtém as camadas via helper da classe base (handles nomeados) e recusa
        # CRS diferentes.
        srcA, srcB = self.get_pair(inputs, operacao="operação de interseção")

        # Higiene: remove nulas/vazias e avisa sobre inválidas (podem inflar a memória).
        srcA = _clean_layer(srcA, "A")
        srcB = _clean_layer(srcB, "B")
        if srcA.empty or srcB.empty:
            logger.warning("Interseção: uma das camadas ficou sem geometrias válidas — resultado vazio.")
            return {"output": gpd.GeoDataFrame(columns=['geometry'], geometry='geometry', crs=srcA.crs)}

        # Tipos geométricos suportados — conferidos DEPOIS da higiene, sobre o que
        # de fato vai para o overlay (por isso não é o `tipos_suportados` do get_pair).
        reject_unsupported_geom_types(srcA, srcB, operation="operação de interseção")

        logger.info(f"Camada A: {len(srcA)} feições, Camada B: {len(srcB)} feições")

        try:
            result = await asyncio.to_thread(_overlay_intersection_bounded, srcA, srcB)
        except MemoryError as e:
            # Mesmo com blocos adaptativos, UMA feição de A que cruza um número
            # enorme de feições de B pode estourar. Mensagem acionável, não crash cru.
            logger.error(f"Interseção sem memória: {e}")
            raise RuntimeError(
                "Interseção excedeu a memória disponível: o cruzamento gera um número enorme de "
                "pares candidatos — normalmente uma feição de extensão muito grande (ou inválida) em "
                "uma camada cruzando muitas feições da outra. Possíveis soluções: recortar/filtrar as "
                "camadas para a área de interesse antes (nós Clip/SpatialFilter), validar/corrigir "
                "geometrias inválidas, ou executar a interseção no banco (PostGIS). É possível também "
                "reduzir INTERSECTION_TARGET_PAIRS no executor para blocos menores."
            )
        except Exception as e:
            logger.error(f"Erro na interseção: {e}")
            raise RuntimeError(f"Erro na operação de interseção: {e}")

        # Consolidação de colunas duplicadas col_1 / col_2
        to_merge = {}
        for col in result.columns:
            if col.endswith('_1'):
                base = col[:-2]
                col2 = f"{base}_2"
                if col2 in result.columns:
                    if result[col].equals(result[col2]):
                        to_merge[base] = result[col]
                        result.drop(columns=[col, col2], inplace=True)

        for col, series in to_merge.items():
            result[col] = series

        if result.empty:
            logger.warning("Resultado vazio na interseção.")
            return {"output": gpd.GeoDataFrame(columns=['geometry'], geometry='geometry', crs=srcA.crs)}

        return {"output": result}
