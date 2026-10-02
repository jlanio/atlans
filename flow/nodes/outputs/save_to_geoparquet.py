import asyncio
import os
import tempfile

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


@register_node
class SaveToGeoParquetNode(BaseNode):
    """
    Salva um GeoDataFrame como GeoParquet e faz upload para o MinIO como artefato.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SaveToGeoParquet',
            'alias': 'Salvar em GeoParquet',
            'description': (
                'Salva um GeoDataFrame em arquivo GeoParquet (.parquet) no armazenamento '
                'da plataforma ou apenas no disco do executor, conforme a localidade dos '
                'dados. Opcionalmente tambem salva num caminho local (legado).'
            ),
            'type': 'output',
            'dynamic_output': False,
            'outputs': [
                {'name': 'filePath', 'type': 'string', 'description': 'Caminho local do arquivo (vazio se apenas MinIO)'},
                {'name': 'artifact_filename', 'type': 'string', 'description': 'Nome do arquivo no MinIO'},
                {'name': 'artifact_s3_key', 'type': 'string', 'description': 'Chave S3 do artefato no MinIO'},
            ],
            'properties': [
                {
                    'name': 'label',
                    'label': 'Nome do artefato',
                    'type': 'string',
                    'default': '',
                    'description': 'Nome do artefato (usado como nome do arquivo no MinIO). Ex: dados_processados',
                },
                {
                    'name': 'outputPath',
                    'label': 'Caminho local',
                    'type': 'string',
                    'default': '',
                    'description': '(Opcional, legado) Caminho local para salvar o arquivo. Se vazio, salva apenas no MinIO.',
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
                    # Nao ha download a proteger num artefato que fica no executor.
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
            # Nao ha download a proteger num artefato que fica no executor.
            credential_id = None

        # Mesma regra de save_geojson: label explicito, senao o basename do
        # outputPath, senao erro. `BaseNode.derive_label` e o ponto unico.
        label = self.derive_label(label, output_path)

        workspace_id, task_id = self.require_execution_context()

        # Obtem o GeoDataFrame
        data = self.get_first_gdf(inputs)

        # Reprojeta se necessario
        data = await asyncio.to_thread(ensure_gdf_crs, data, crs)

        features = len(data)
        safe_label = slugify_label(label)

        # Valida path contra path traversal
        if output_path:
            output_path = validate_file_path(output_path, write=True)

        # Escrita local (backward compat)
        file_path = ''
        if output_path:
            file_path = ensure_extension(output_path, '.parquet')
            outdir = os.path.dirname(file_path)
            if outdir and not os.path.exists(outdir):
                os.makedirs(outdir, exist_ok=True)
            logger.info(f"Salvando {features} feicoes em GeoParquet local: {file_path}")
            await asyncio.to_thread(data.to_parquet, file_path)

        # Gera Parquet em arquivo temporario e faz upload para MinIO
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            await asyncio.to_thread(data.to_parquet, tmp_path)

            filename = f"{safe_label}.parquet"

            # `persistir_artefato` le o fileobj inteiro nos dois caminhos
            # (executor e MinIO), entao o ramo `if tamanho > 10MB: fileobj
            # else: content` que existia aqui produzia exatamente o mesmo
            # resultado nas duas pontas.
            with open(tmp_path, 'rb') as f:
                s3_key, artifact_meta = await asyncio.to_thread(
                    persistir_artefato,
                    localidade=localidade,
                    fileobj=f,
                    filename=filename,
                    content_type='application/vnd.apache.parquet',
                    workspace_id=workspace_id,
                    task_id=task_id,
                    label=label,
                    fmt='geoparquet',
                    features=features,
                    credential_id=credential_id,
                )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError as exc:
                logger.debug("Falha ao remover arquivo temporário '%s': %s", tmp_path, exc)

        self.log(descrever_localidade(localidade, quem))
        onde = 'neste executor' if localidade == EXECUTOR else 'no MinIO'
        self.log(f"Artefato salvo {onde}: {s3_key} (geoparquet, {features} feicoes)")

        return {
            'output': {
                'filePath': file_path,
                'artifact_filename': filename,
                'artifact_s3_key': s3_key,
            },
            '__artifact__': artifact_meta,
        }
