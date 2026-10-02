import asyncio


from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import validate_file_path, gdf_para_geojson, slugify_label
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
class SaveGeoJSON(BaseNode):
    @classmethod
    def description(cls) -> dict:
        return {
            'name': 'SaveGeoJSON',
            'alias': 'Salvar em GeoJSON',
            'description': (
                'Salva um GeoDataFrame como arquivo .geojson no armazenamento da '
                'plataforma ou apenas no disco do executor, conforme a localidade '
                'dos dados. Opcionalmente tambem salva num caminho local (legado).'
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
                    'description': 'Nome do artefato (usado como nome do arquivo no MinIO). Ex: resultado_buffer',
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
                    'description': 'CRS para o GeoDataFrame antes de salvar',
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

    async def execute(self, inputs: dict) -> dict:
        self.validate()
        output_path = self.get_param('outputPath', '').strip()
        crs = self.get_param('crs', 'EPSG:4326')
        credential_id = self.get_param('credential_id', '') or None
        localidade, quem = resolver_localidade(self.get_param('localidade', None))
        if localidade == EXECUTOR:
            # Nao ha download a proteger num artefato que fica no executor.
            credential_id = None
        label = self.derive_label(self.get_param('label', ''), output_path)
        workspace_id, _ = self.require_execution_context()

        # Obtem o GeoDataFrame
        data = self.get_first_gdf(inputs)

        # Reprojeta e serializa para GeoJSON string (sem tocar no GDF do pai)
        geojson_str = await asyncio.to_thread(gdf_para_geojson, data, crs)
        content = geojson_str.encode('utf-8')
        features = len(data)

        # Escrita local (backward compat)
        file_path = ''
        if output_path:
            raw_out = output_path if output_path.endswith('.geojson') else output_path + '.geojson'
            validated = validate_file_path(raw_out, write=True)
            file_path = str(validated)
            with open(file_path, 'w', encoding='utf-8') as fh:
                fh.write(geojson_str)
            self.log(f"Arquivo salvo localmente: {file_path}")

        # Upload para MinIO
        safe_label = slugify_label(label)
        filename = f"{safe_label}.geojson"

        s3_key, artifact_meta = await asyncio.to_thread(
            persistir_artefato,
            localidade=localidade,
            content=content,
            filename=filename,
            content_type='application/geo+json',
            workspace_id=workspace_id,
            task_id=self._task_id,
            label=label,
            fmt='geojson',
            features=features,
            credential_id=credential_id,
        )
        self.log(descrever_localidade(localidade, quem))
        onde = 'neste executor' if localidade == EXECUTOR else 'no MinIO'
        self.log(f"Artefato salvo {onde}: {s3_key} (geojson, {features} feicoes)")

        return {
            'output': {
                'filePath': file_path,
                'artifact_filename': filename,
                'artifact_s3_key': s3_key,
            },
            '__artifact__': artifact_meta,
        }
