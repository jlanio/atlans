"""
DataInput — Data Input from the Workspace Drive or from Artifacts.

Reads a stored file (Drive or Artifacts context), downloads it from MinIO to
temp and loads the data. It's the read-side mirror of DataOutput (output).

Supported formats:
  Geospatial    -> GeoJSON, Shapefile (.zip or .shp), KML/KMZ, GeoPackage (.gpkg)
                -> output: GeoDataFrame (geopandas); a GeoPackage table
                   without geometry comes out as a DataFrame
  Tabular       -> CSV, XLSX, JSON
                -> output: DataFrame (pandas) or list[dict]
  Others        -> raw bytes or dict with metadata
"""
import asyncio
import os
from typing import Any, Dict

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.drive_resolver import resolve_drive_file, resolve_artifact_file

logger = get_logger(__name__)

_GEO_EXTENSIONS = {"geojson", "shp", "zip", "kml", "kmz", "gpkg", "gml", "fgb"}


def _ler_kmz(path: str) -> Any:
    """A KMZ holding a single KML (Google Earth's, and Salvar arquivo's) is
    read through that KML: GDAL's LIBKML, opening the .kmz itself, drops the
    attributes (SchemaData) it reads from the same doc.kml outside the zip. A
    KMZ made of several KML (LIBKML's own, with layers/) is read as it is."""
    import zipfile
    from flow.utils.leitura_geo import read_geodataframe

    with zipfile.ZipFile(path) as kmz:
        kmls = [nome for nome in kmz.namelist() if nome.lower().endswith(".kml")]
        if len(kmls) == 1:
            return read_geodataframe(kmz.read(kmls[0]))
    return read_geodataframe(path)


def _load_file(path: str, ext: str, crs: str) -> Any:
    """Carrega o arquivo de forma sincrona."""
    try:
        if ext in _GEO_EXTENSIONS:
            import geopandas as gpd
            from flow.utils.leitura_geo import read_geodataframe
            gdf = _ler_kmz(path) if ext == "kmz" else read_geodataframe(path)
            # A GeoPackage can hold a table without geometry (Salvar arquivo
            # writes one): it comes back as a DataFrame, with no CRS to touch.
            if not isinstance(gdf, gpd.GeoDataFrame):
                return gdf
            if crs and gdf.crs is not None and str(gdf.crs) != crs:
                gdf = gdf.to_crs(crs)
            elif gdf.crs is None and crs:
                gdf = gdf.set_crs(crs)
            return gdf

        if ext == "csv":
            from flow.utils.leitura_csv import ler_csv
            return ler_csv(path)

        if ext == "xlsx":
            # Through GDAL, which the executor ships: pandas.read_excel needs
            # openpyxl, which it does not, and failed on every .xlsx. FORCE: the
            # first row is the header, as pandas reads it (GDAL only guesses so
            # when a row below it has a number).
            from flow.utils.leitura_geo import read_geodataframe
            return read_geodataframe(path, read_geometry=False, HEADERS="FORCE")

        if ext == "xls":
            import pandas as pd
            return pd.read_excel(path)

        if ext == "json":
            import json
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        with open(path, "rb") as f:
            return f.read()
    finally:
        # Limpa arquivo temporario
        try:
            os.unlink(path)
        except OSError:
            pass


@register_node
class DataInput(BaseNode):
    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "DataInput",
            "alias": "Entrada de Dados",
            "description": (
                "Carrega um arquivo armazenado no Drive do Workspace ou um "
                "Artefato de execucao anterior e o expoe como dado de entrada. "
                "Suporta GeoJSON, Shapefile, KML, KMZ, GeoPackage, CSV, XLSX e JSON."
            ),
            "type": "datasource",
            "dynamic_output": True,
            "properties": [
                {
                    "name": "context",
                    "label": "Origem",
                    "type": "select",
                    "default": "drive",
                    "description": "De onde ler os dados.",
                    "options": [
                        {"value": "drive",     "label": "Drive do Workspace"},
                        {"value": "artifacts", "label": "Artefatos"},
                    ],
                },
                {
                    "name": "driveFileId", "required": True,
                    "label": "Arquivo do Drive",
                    "type": "drive",
                    "default": "",
                    "description": "Arquivo do Drive do Workspace a ser carregado.",
                    "visibleWhen": {"field": "context", "in": ["drive"]},
                },
                {
                    "name": "artifactId", "required": True,
                    "label": "Artefato",
                    "type": "artifact",
                    "default": "",
                    "description": "Artefato de execucao anterior a ser carregado.",
                    "visibleWhen": {"field": "context", "in": ["artifacts"]},
                },
                {
                    "name": "crs",
                    "label": "CRS de saída",
                    "type": "string",
                    "default": "EPSG:4326",
                    "description": "CRS de saida para arquivos geoespaciais.",
                },
            ],
            "outputs": [
                {"name": "output", "type": "object", "description": "Dados carregados do arquivo", "port": True},
                {"name": "metadata", "type": "object", "description": "Metadados do arquivo", "port": True},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        context: str = self.get_param("context", "drive")
        crs: str = self.get_param("crs", "EPSG:4326").strip()
        workspace_id: str | None = getattr(self, "_workspace_id", None)

        if context == "artifacts":
            file_id: str = self.get_param("artifactId", "").strip()
            if not file_id:
                raise ValueError("Parametro 'artifactId' e obrigatorio no contexto Artefatos.")
            logger.info("DataInput: resolvendo artefato id=%s workspace=%s", file_id, workspace_id)
            temp_path, ext, original_name = await asyncio.to_thread(
                resolve_artifact_file, file_id
            )
        else:
            file_id = self.get_param("driveFileId", "").strip()
            if not file_id:
                raise ValueError("Parametro 'driveFileId' e obrigatorio no contexto Drive.")
            logger.info("DataInput: resolvendo arquivo id=%s workspace=%s", file_id, workspace_id)
            temp_path, ext, original_name = await asyncio.to_thread(
                resolve_drive_file, file_id
            )

        logger.info("DataInput: carregando '%s' (ext=%s)", original_name, ext)
        data = await asyncio.to_thread(_load_file, temp_path, ext, crs)

        metadata = {
            "context": context,
            "file_id": file_id,
            "original_name": original_name,
            "extension": ext,
        }

        import geopandas as gpd
        import pandas as pd
        if isinstance(data, gpd.GeoDataFrame):
            logger.info("DataInput: GeoDataFrame — %d feicoes, CRS: %s", len(data), data.crs)
        elif isinstance(data, pd.DataFrame):
            logger.info("DataInput: DataFrame — %d linhas x %d colunas", *data.shape)

        return {"output": data, "metadata": metadata}
