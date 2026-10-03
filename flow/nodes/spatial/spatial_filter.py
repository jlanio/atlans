# flow/nodes/spatial/spatial_filter.py
"""
Spatial Filter node — filters features by bounding box or by another layer (mask).
"""
import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import align_crs
from flow.utils.logger import get_logger

logger = get_logger(__name__)



@register_node
class SpatialFilterNode(BaseNode):

    @classmethod
    def description(cls):
        return {
            "name": "SpatialFilterNode",
            "alias": "Filtro Espacial",
            "description": (
                "Mantém (ou descarta, com 'Inverter') as feições da camada de entrada "
                "conforme a relação espacial com uma caixa delimitadora ou com uma "
                "camada de máscara."
            ),
            "type": "spatial",
            "properties": [
                {
                    "name": "filter_mode",
                    "label": "Modo de filtro",
                    "type": "select",
                    "default": "mask",
                    "description": "Contra o que filtrar as feições.",
                    "options": [
                        {"value": "mask", "label": "Por outra camada (máscara)"},
                        {"value": "bbox", "label": "Por caixa delimitadora"},
                    ],
                },
                {
                    "name": "predicate",
                    "label": "Relação espacial",
                    "type": "select",
                    "default": "intersects",
                    "description": "Relação geométrica entre a feição e a máscara.",
                    "options": [
                        {"value": "intersects", "label": "Intersecta"},
                        {"value": "within",     "label": "Está contida na máscara"},
                        {"value": "contains",   "label": "Contém a máscara"},
                        {"value": "overlaps",   "label": "Sobrepõe"},
                    ],
                    "visibleWhen": {"field": "filter_mode", "in": ["mask"]},
                },
                {
                    "name": "bbox",
                    "label": "Caixa delimitadora",
                    "type": "string",
                    "default": "",
                    "description": "Formato 'minx,miny,maxx,maxy', nas unidades do CRS da camada.",
                    "visibleWhen": {"field": "filter_mode", "in": ["bbox"]},
                },
                {
                    "name": "invert",
                    "label": "Inverter seleção",
                    "type": "boolean",
                    "default": False,
                    "description": "Mantém as feições que NÃO satisfazem a relação (o complemento).",
                },
            ],
            "inputs": [
                {"name": "layer", "type": "geodataframe", "description": "Camada de feições a filtrar."},
                {"name": "mask", "type": "geodataframe", "description": "Camada de máscara (usada no modo 'Por outra camada')."},
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe", "description": "Feições filtradas"},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        filter_mode = self.parameters.get("filter_mode", "mask").strip().lower()
        predicate = self.parameters.get("predicate", "intersects").strip().lower()
        invert = bool(self.parameters.get("invert", False))
        # filter_mode/predicate already validated against the options by self.validate().

        gdf = self.get_input_gdf(inputs, "layer")

        if filter_mode == "bbox":
            bbox_str = self.parameters.get("bbox", "")
            if not bbox_str:
                raise ValueError("Parâmetro 'Caixa delimitadora' obrigatório no modo 'Por caixa delimitadora'.")
            parts = [float(v.strip()) for v in bbox_str.split(",")]
            if len(parts) != 4:
                raise ValueError("A caixa delimitadora deve ter exatamente 4 valores: minx,miny,maxx,maxy.")

            def _bbox_filter(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
                inside = gdf.cx[parts[0]:parts[2], parts[1]:parts[3]]
                return gdf.drop(index=inside.index) if invert else inside

            result = await asyncio.to_thread(_bbox_filter, gdf)

        else:  # mask
            # The mask is an OPTIONAL port (only applies in this mode), and the message says
            # which mode requires it — that is why it does not go through get_pair/get_input_gdf.
            mask_gdf = inputs.get("mask")
            if mask_gdf is None or not isinstance(mask_gdf, gpd.GeoDataFrame) or mask_gdf.empty:
                raise ValueError(
                    "Modo 'Por outra camada' exige a entrada 'mask' conectada e não vazia."
                )

            def _mask_filter(gdf: gpd.GeoDataFrame, mask_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
                # Mask in the layer's CRS when both have a CRS and they differ —
                # here, in the thread: to_crs is O(n) and ran on the event loop.
                mask_gdf = align_crs(gdf, mask_gdf)
                if predicate == "intersects":
                    # Indexed spatial join (STRtree): avoids the expensive unary_union
                    # and the elementwise predicate over the whole layer. For
                    # 'intersects', "intersects the union" ⟺ "intersects SOME
                    # feature of the mask", so the result is identical to the old one.
                    #
                    # reset_index(drop=True): the selection is POSITIONAL, immune to
                    # a duplicated index (concat/explode/read_parquet upstream) —
                    # with a non-unique index, isin by label would over-select.
                    # [["geometry"]]: drops any pre-existing 'index_right' column
                    # (e.g. output of a previous SpatialJoin), which would
                    # otherwise make sjoin itself raise ValueError.
                    base = gdf.reset_index(drop=True)
                    matched = gpd.sjoin(
                        base[["geometry"]], mask_gdf[["geometry"]],
                        predicate="intersects", how="inner",
                    ).index.unique()
                    hits = base.index.isin(matched)  # np.ndarray[bool], by position
                    return gdf[~hits] if invert else gdf[hits]
                # within/contains/overlaps are NOT monotonic under union (being
                # "inside the union" ≠ "inside a feature"), so they keep the
                # unary_union path to preserve the semantics exactly.
                from shapely.ops import unary_union
                mask_geom = unary_union(mask_gdf.geometry.values)
                hits = getattr(gdf.geometry, predicate)(mask_geom)
                return gdf[~hits] if invert else gdf[hits]

            result = await asyncio.to_thread(_mask_filter, gdf, mask_gdf)

        logger.info(
            "Filtro espacial (%s/%s%s): %d/%d feições retidas.",
            filter_mode, predicate if filter_mode == "mask" else "bbox",
            ", invertido" if invert else "", len(result), len(gdf),
        )
        return {"output": result}
