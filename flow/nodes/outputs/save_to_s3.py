import asyncio
import os

from typing import Any, Dict

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.artifact_helpers import (
    EXECUTOR,
    descrever_localidade,
    persistir_artefato,
    propriedade_localidade,
    resolver_localidade,
)
from flow.utils.geo_helpers import ensure_gdf_crs, gdf_para_geojson, slugify_label
from flow.utils.logger import get_logger
from flow.utils.s3_cliente import cliente_s3

logger = get_logger(__name__)


def _upload_to_s3(
    json_str: str,
    bucket: str,
    key: str,
    *,
    s3_auth: Dict[str, Any] | None,
    region: str,
    aws_access_key_id: str | None,
    aws_secret_access_key: str | None,
) -> None:
    """
    Helper bloqueante: envia uma string JSON para um objeto em bucket S3.
    """
    s3 = cliente_s3(
        s3_auth,
        region=region,
        access_key_id=aws_access_key_id,
        secret_access_key=aws_secret_access_key,
    )
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json_str.encode('utf-8'),
        ContentType='application/geo+json'
    )


@register_node
class SaveToS3Node(BaseNode):
    """
    Serializa um GeoDataFrame como GeoJSON e faz upload para um bucket AWS S3.

    A autenticação vem de uma credencial `s3` do cofre: o servidor a resolve e
    injeta em `s3_auth` (chave, segredo, região, bucket padrão e endpoint) — o
    segredo nunca fica na definition. Sem credencial, vale a cadeia padrão do
    boto3 (IAM role, variáveis de ambiente, ~/.aws/credentials).

    `awsAccessKeyId`/`awsSecretAccessKey` são os campos antigos, digitados no
    nó: seguem lidos para o fluxo gravado continuar funcionando com a mesma
    identidade, mas o segredo gravado ali é recusado ao salvar e redigido na
    leitura (é chave secreta como `password`).

    O `credential_id` aceita também um Webhook Token — o uso antigo do campo, que
    protege o download da cópia registrada como artefato. O servidor só injeta a
    do tipo `s3` (e tira o id); qualquer outro id que chegue aqui é tratado como
    esse token.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SaveToS3',
            'alias': 'Salvar no S3',
            'description': (
                'Serializa um GeoDataFrame como GeoJSON e envia para um bucket S3 externo. '
                'Opcionalmente registra uma copia no MinIO interno como artefato.'
            ),
            'type': 'output',
            'dynamic_output': False,
            'outputs': [
                {'name': 's3Uri', 'type': 'string', 'description': 'URI S3 do objeto criado (s3://bucket/key)'},
                {'name': 'artifact_s3_key', 'type': 'string', 'description': 'Chave S3 no MinIO (vazio se registerArtifact=false)'},
            ],
            'properties': [
                {
                    'name': 'credential_id',
                    'label': 'Credencial S3',
                    'type': 'credential',
                    'default': '',
                    'description': (
                        'Credencial S3 do cofre (chave de acesso, segredo, região, bucket padrão e '
                        'endpoint para MinIO/S3-compatíveis). Vazio: a cadeia padrão do boto3 no '
                        'executor. Um Webhook Token aqui, em vez dela, só protege o download da '
                        'cópia registrada como artefato.'
                    ),
                    'credential_types': ['s3', 'webhook_token'],
                },
                {
                    # Injetada pelo servidor a partir da credencial `s3` (ver
                    # credential_resolver). Declarada porque `validate()`
                    # reconstrói os parâmetros a partir desta lista e descartaria
                    # o que não estivesse nela. A UI a esconde pelo nome.
                    'name': 's3_auth',
                    'label': 'Credencial S3 resolvida',
                    'type': 'object',
                    'default': {},
                    'description': 'Preenchida automaticamente a partir da credencial S3 escolhida. '
                                   'Nao editavel: o segredo nunca e gravado na definicao do workflow.',
                },
                {
                    'name': 'bucketName',
                    'label': 'Bucket S3',
                    'type': 'string',
                    'default': '',
                    'description': 'Nome do bucket S3 de destino. Vazio: o bucket padrão da credencial S3.',
                },
                {
                    'name': 'key', 'required': True,
                    'label': 'Caminho no bucket (key)',
                    'type': 'string',
                    'default': '',
                    'description': 'Chave (caminho) do objeto dentro do bucket S3.',
                },
                {
                    'name': 'region',
                    'label': 'Região',
                    'type': 'string',
                    'default': '',
                    'description': 'Regiao AWS do bucket S3. Vazio: a da credencial S3, ou us-east-1.',
                },
                {
                    'name': 'awsAccessKeyId',
                    'label': 'Chave de acesso AWS (obsoleto)',
                    'type': 'string',
                    'default': '',
                    'description': 'Obsoleto: use uma credencial S3. Lido só quando nenhuma credencial S3 foi escolhida.',
                },
                {
                    'name': 'awsSecretAccessKey',
                    'label': 'Chave secreta AWS (obsoleto)',
                    'type': 'string',
                    'default': '',
                    'description': (
                        'Obsoleto: use uma credencial S3. Segredo gravado aqui fica em texto puro na '
                        'definição e por isso é recusado ao salvar — apague o valor e escolha a credencial.'
                    ),
                },
                {
                    'name': 'crs',
                    'label': 'CRS de destino',
                    'type': 'string',
                    'default': 'EPSG:4326',
                    'description': 'CRS de destino antes de serializar. Se diferente do CRS atual, realiza reprojecao.',
                },
                {
                    'name': 'registerArtifact',
                    'label': 'Registrar como artefato',
                    'type': 'boolean',
                    'default': False,
                    'description': 'Se verdadeiro, tambem salva uma copia no MinIO interno e registra como artefato.',
                },
                {
                    'name': 'label',
                    'label': 'Nome do artefato',
                    'type': 'string',
                    'default': '',
                    'description': 'Nome do artefato no MinIO (usado apenas quando registerArtifact=true).',
                },
                # Vale so para a COPIA registrada como artefato. O bucket S3
                # externo e um destino que quem monta o fluxo configurou
                # explicitamente, com credencial propria — a localidade aqui
                # trata do armazenamento da plataforma, nao de para onde o
                # usuario decidiu mandar o dado dele.
                propriedade_localidade(
                    visible_when={'field': 'registerArtifact', 'in': [True, 'true']}
                ),
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        s3_auth = self.get_param('s3_auth') or {}
        if not isinstance(s3_auth, dict):
            s3_auth = {}
        bucket = (self.get_param('bucketName', '') or '').strip() or str(s3_auth.get('bucket') or '').strip()
        key = self.get_param('key', '').strip()
        region = (
            (self.get_param('region', '') or '').strip()
            or str(s3_auth.get('region') or '').strip()
            or 'us-east-1'
        )
        aws_access_key_id = (self.get_param('awsAccessKeyId', '') or '').strip() or None
        aws_secret_access_key = (self.get_param('awsSecretAccessKey', '') or '').strip() or None
        crs = self.get_param('crs', 'EPSG:4326')
        register_artifact = self.get_param('registerArtifact', False)
        label = self.get_param('label', '').strip()
        # Com a credencial S3 resolvida o servidor já tirou o id; o que sobra
        # aqui é o Webhook Token que protege a cópia registrada (uso antigo).
        credential_id = self.get_param('credential_id', '') or None

        # Sobrou `credential_id` sem `s3_auth`: a credencial escolhida NÃO foi
        # resolvida (apagada, vencida, de outro tipo, ou privada de quem não
        # disparou). Sem cópia registrada, esse id não pode ser o Webhook Token
        # do uso antigo — o servidor o tira nesse caso —, e seguir faria o
        # upload com OUTRA identidade (as chaves antigas do nó ou a cadeia
        # padrão do boto3 no executor), em silêncio. Mesma regra do HttpRequest.
        if credential_id and not s3_auth and not register_artifact:
            raise ValueError(
                "A credencial escolhida para este nó não pôde ser resolvida — ela pode ter "
                "sido apagada, estar vencida, não estar acessível a quem disparou a execução, "
                "ou não ser do tipo S3. O upload NÃO foi feito, para não escrever no bucket "
                "com outra identidade."
            )
        if credential_id and not s3_auth:
            self.log(
                "credential_id sem credencial S3 resolvida: tratado como o Webhook Token que "
                "protege a copia; o upload usa as chaves antigas do no ou a cadeia padrao do "
                "boto3 no executor."
            )

        endpoint = str(s3_auth.get('endpoint_url') or '').strip()
        if endpoint:
            # Mesma guarda do teste de conexão da credencial: um endpoint que o
            # teste recusaria não passa a valer aqui.
            from flow.utils.geo_helpers import validate_url_ssrf
            await asyncio.to_thread(validate_url_ssrf, endpoint)

        if not bucket:
            raise ValueError("Parametro 'bucketName' e obrigatorio (ou um bucket padrao na credencial S3).")
        if not key:
            raise ValueError("Parametro 'key' e obrigatorio.")

        # Obtem o GeoDataFrame
        data = self.get_first_gdf(inputs)

        # Reprojeta se necessario. Fica FORA do try abaixo: um CRS de destino
        # invalido nao e erro de serializacao, e a mensagem diria o contrario.
        data = await asyncio.to_thread(ensure_gdf_crs, data, crs)

        features = len(data)
        logger.info(f"Serializando {features} feicoes para GeoJSON...")
        try:
            json_str = await asyncio.to_thread(gdf_para_geojson, data, nat_como_nulo=True)
        except Exception as e:
            raise RuntimeError(f"Erro ao serializar GeoDataFrame para GeoJSON: {e}") from e

        # Upload para S3 externo
        logger.info(f"Enviando para s3://{bucket}/{key} (regiao: {region})")
        try:
            await asyncio.to_thread(
                _upload_to_s3, json_str, bucket, key,
                s3_auth=s3_auth,
                region=region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
        except ImportError:
            raise
        except Exception as e:
            logger.error(f"Erro ao enviar para S3 (bucket='{bucket}', key='{key}'): {e}")
            raise RuntimeError(f"Erro ao enviar para S3: {e}") from e

        s3_uri = f"s3://{bucket}/{key}"
        logger.info(f"Arquivo enviado com sucesso: {s3_uri}")

        output_data: Dict[str, Any] = {'s3Uri': s3_uri, 'artifact_s3_key': ''}
        result: Dict[str, Any] = {}

        # Registro opcional como artefato no MinIO interno
        if register_artifact:
            workspace_id, task_id = self.require_execution_context()

            if not label:
                label = os.path.splitext(os.path.basename(key))[0] or 's3_export'

            safe_label = slugify_label(label)
            filename = f"{safe_label}.geojson"
            content = json_str.encode('utf-8')

            localidade, quem = resolver_localidade(self.get_param('localidade', None))
            if localidade == EXECUTOR:
                credential_id = None
            elif s3_auth and not credential_id:
                # O `credential_id` foi a credencial S3 (o servidor a injetou e
                # tirou o id): não sobra Webhook Token para proteger a cópia.
                self.log(
                    "Copia registrada sem token de protecao: a credencial escolhida e a "
                    "do S3, e o download da copia fica pelo link."
                )

            minio_key, artifact_meta = await asyncio.to_thread(
                persistir_artefato,
                localidade=localidade,
                content=content,
                filename=filename,
                content_type='application/geo+json',
                workspace_id=workspace_id,
                task_id=task_id,
                label=label,
                fmt='geojson',
                features=features,
                credential_id=credential_id,
            )
            self.log(descrever_localidade(localidade, quem))
            onde = 'neste executor' if localidade == EXECUTOR else 'no MinIO'
            self.log(f"Copia do artefato salva {onde}: {minio_key}")
            output_data['artifact_s3_key'] = minio_key
            result['__artifact__'] = artifact_meta

        result['output'] = output_data
        return result
