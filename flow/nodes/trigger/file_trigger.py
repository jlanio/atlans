# flow/nodes/trigger/file_trigger.py
import asyncio
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.leitura_geo import ler_geodataframe
from flow.utils.logger import get_logger

logger = get_logger(__name__)

@register_node
class FileTrigger(BaseNode):
    @classmethod
    def description(cls) -> dict:
        return {
            'name': 'FileTrigger',
            'alias': 'Gatilho por Arquivo',
            'description': 'Carrega dois arquivos do disco do executor e os retorna como '
                           'GeoDataFrames. Formatos aceitos: .shp, .geojson, .gpkg, .parquet '
                           'e .csv com geometria.',
            'type': 'trigger',
            'properties': [
                {'name': 'pathA', 'required': True, 'placeholder': '/caminho/para/arquivo_a.shp',
                 'label': 'Arquivo A (sai pela porta file_a)', 'type': 'string', 'default': '',
                 'description': 'Caminho no disco do executor. O dado carregado sai pela porta file_a.'},
                {'name': 'pathB', 'required': True, 'placeholder': '/caminho/para/arquivo_b.shp',
                 'label': 'Arquivo B (sai pela porta file_b)', 'type': 'string', 'default': '',
                 'description': 'Caminho no disco do executor. O dado carregado sai pela porta file_b.'},
            ],
            'outputs': [
                {'name': 'file_a', 'type': 'geodataframe', 'description': 'Primeiro arquivo carregado como GeoDataFrame', 'port': True},
                {'name': 'file_b', 'type': 'geodataframe', 'description': 'Segundo arquivo carregado como GeoDataFrame', 'port': True},
            ],
        }

    async def execute(self, inputs: dict) -> dict:
        self.validate()
        path_a = self.parameters.get('pathA')
        path_b = self.parameters.get('pathB')

        if not path_a or not path_b:
            raise ValueError("Parâmetros 'pathA' e 'pathB' são obrigatórios.")

        # Os caminhos vêm do workflow, portanto de quem edita o fluxo — sem este
        # guard o nó lia QUALQUER arquivo do host do executor (chaves, certificado
        # mTLS, .env) e devolvia o conteúdo como GeoDataFrame no output do run.
        # validate_file_path resolve o caminho e exige que esteja dentro de
        # ALLOWED_FILE_DIRS; é o mesmo guard já usado pelos demais nós de arquivo.
        from flow.utils.geo_helpers import validate_file_path
        safe_a = validate_file_path(path_a)
        safe_b = validate_file_path(path_b)

        for p in (safe_a, safe_b):
            if not p.exists():
                raise FileNotFoundError(f"Caminho não encontrado: {p}")

        # Carrega shapefiles de forma assíncrona para não bloquear o loop.
        # `ler_geodataframe` recusa conteudo VRT / caminho virtual do GDAL.
        gdf1 = await asyncio.to_thread(ler_geodataframe, str(safe_a))
        gdf2 = await asyncio.to_thread(ler_geodataframe, str(safe_b))

        logger.info(f"Arquivos carregados: {safe_a}, {safe_b}")
        return {"file_a": gdf1, "file_b": gdf2}
