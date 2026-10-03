import asyncio
import os
import tempfile
import zipfile

import geopandas as gpd
from typing import Any, Dict

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import ensure_extension, validate_file_path, ensure_gdf_crs, slugify_label
from flow.utils.artifact_helpers import (
    EXECUTOR,
    descrever_localidade,
    persistir_artefato,
    propriedade_localidade,
    resolver_localidade,
)
from flow.utils.logger import get_logger

logger = get_logger(__name__)


def _save_shapefile(gdf: gpd.GeoDataFrame, file_path: str) -> None:
    """
    Blocking helper: saves the GeoDataFrame to an ESRI Shapefile.
    Warns about column-name truncation (the Shapefile's 10-character limit).
    """
    long_cols = [col for col in gdf.columns if len(col) > 10 and col != gdf.geometry.name]
    if long_cols:
        logger.warning(
            f"As seguintes colunas possuem nomes com mais de 10 caracteres e serao truncadas "
            f"no Shapefile: {long_cols}"
        )
    gdf.to_file(file_path, driver='ESRI Shapefile')


def _zip_shapefile_dir(shp_dir: str, zip_path: str) -> None:
    """Packs all the files in the Shapefile's directory into a single .zip."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(shp_dir):
            fpath = os.path.join(shp_dir, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, fname)


@register_node
class SaveToShapefileNode(BaseNode):
    """
    Saves a GeoDataFrame as an ESRI Shapefile, packs it into a .zip
    and uploads it to MinIO as an artifact.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SaveToShapefile',
            'alias': 'Salvar em Shapefile',
            'description': (
                'Salva um GeoDataFrame como Shapefile ESRI (.shp) compactado em .zip no '
                'armazenamento da plataforma ou apenas no disco do executor, conforme a '
                'localidade dos dados. Opcionalmente tambem salva num caminho local (legado).'
            ),
            'type': 'output',
            'dynamic_output': False,
            'outputs': [
                {'name': 'filePath', 'type': 'string', 'description': 'Caminho local do Shapefile (vazio se apenas MinIO)'},
                {'name': 'artifact_filename', 'type': 'string', 'description': 'Nome do arquivo .zip no MinIO'},
                {'name': 'artifact_s3_key', 'type': 'string', 'description': 'Chave S3 do artefato no MinIO'},
            ],
            'properties': [
                {
                    'name': 'label',
                    'label': 'Nome do artefato',
                    'type': 'string',
                    'default': '',
                    'description': 'Nome do artefato (usado como nome do arquivo no MinIO). Ex: areas_buffer',
                },
                {
                    'name': 'outputPath',
                    'label': 'Caminho local',
                    'type': 'string',
                    'default': '',
                    'description': '(Opcional, legado) Caminho local para salvar o Shapefile. Se vazio, salva apenas no MinIO.',
                },
                {
                    'name': 'crs',
                    'label': 'CRS de destino',
                    'type': 'string',
                    'default': 'EPSG:4326',
                    'description': 'CRS de destino. Se diferente do CRS atual, realiza reprojecao antes de salvar.',
                },
                {
                    'name': 'credential_id',
                    'type': 'credential',
                    'default': '',
                    'description': 'Token Bearer para proteger o download. Sem credencial, o artefato e publico.',
                    'credential_types': ['webhook_token'],
                    # There is no download to protect on an artifact that stays on the executor.
                    'visibleWhen': {'field': 'localidade', 'in': ['herdar']},
                },
                propriedade_localidade(),
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        label = self.get_param('label', '').strip()
        output_path = self.get_param('outputPath', '').strip()
        crs = self.get_param('crs', 'EPSG:4326')
        credential_id = self.get_param('credential_id', '') or None
        localidade, quem = resolver_localidade(self.get_param('localidade', None))
        if localidade == EXECUTOR:
            # There is no download to protect on an artifact that stays on the executor.
            credential_id = None

        # Same rule as save_geojson: explicit label, otherwise the basename of
        # outputPath, otherwise an error. `BaseNode.derive_label` is the single point.
        label = self.derive_label(label, output_path)

        workspace_id, task_id = self.require_execution_context()

        # Obtem o GeoDataFrame
        data = self.get_first_gdf(inputs)

        # Reprojects if needed
        data = await asyncio.to_thread(ensure_gdf_crs, data, crs)

        features = len(data)
        safe_label = slugify_label(label)

        # Valida path contra path traversal
        if output_path:
            output_path = validate_file_path(output_path, write=True)

        # Escrita local (backward compat)
        file_path = ''
        if output_path:
            file_path = ensure_extension(output_path, '.shp')
            outdir = os.path.dirname(file_path)
            if outdir and not os.path.exists(outdir):
                os.makedirs(outdir, exist_ok=True)
            logger.info(f"Salvando {features} feicoes em Shapefile local: {file_path}")
            await asyncio.to_thread(_save_shapefile, data, file_path)

        # Gera Shapefile em diretorio temporario, compacta e faz upload
        with tempfile.TemporaryDirectory() as shp_dir, \
             tempfile.TemporaryDirectory() as zip_dir:
            shp_path = os.path.join(shp_dir, f"{safe_label}.shp")
            await asyncio.to_thread(_save_shapefile, data, shp_path)

            zip_path = os.path.join(zip_dir, f"{safe_label}.zip")
            await asyncio.to_thread(_zip_shapefile_dir, shp_dir, zip_path)

            # Upload of the zip to MinIO
            filename = f"{safe_label}.zip"

            # `persistir_artefato` reads the whole fileobj on both paths
            # (executor and MinIO), so the `if tamanho > 10MB: fileobj
            # else: content` branch that existed here produced exactly the same
            # result at both ends — 12 duplicated lines and a
            # "streaming" comment that was never true.
            with open(zip_path, 'rb') as zf:
                s3_key, artifact_meta = await asyncio.to_thread(
                    persistir_artefato,
                    localidade=localidade,
                    fileobj=zf,
                    filename=filename,
                    content_type='application/zip',
                    workspace_id=workspace_id,
                    task_id=task_id,
                    label=label,
                    fmt='shapefile',
                    features=features,
                    credential_id=credential_id,
                )

        self.log(descrever_localidade(localidade, quem))
        onde = 'neste executor' if localidade == EXECUTOR else 'no MinIO'
        self.log(f"Artefato salvo {onde}: {s3_key} (shapefile/zip, {features} feicoes)")

        return {
            'output': {
                'filePath': file_path,
                'artifact_filename': filename,
                'artifact_s3_key': s3_key,
            },
            '__artifact__': artifact_meta,
        }
