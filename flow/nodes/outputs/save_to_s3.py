import asyncio
import os

from typing import Any, Dict

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.artifact_helpers import (
    EXECUTOR,
    describe_locality,
    persistir_artefato,
    locality_property,
    resolve_locality,
)
from flow.utils.geo_helpers import ensure_gdf_crs, gdf_para_geojson, slugify_label
from flow.utils.logger import get_logger
from flow.utils.s3_cliente import s3_client

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
    Blocking helper: sends a JSON string to an object in an S3 bucket.
    """
    s3 = s3_client(
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
    Serializes a GeoDataFrame as GeoJSON and uploads it to an AWS S3 bucket.

    Authentication comes from an `s3` credential in the vault: the server resolves
    it and injects it into `s3_auth` (key, secret, region, default bucket and
    endpoint) — the secret never stays in the definition. Without a credential, the
    default boto3 chain applies (IAM role, environment variables, ~/.aws/credentials).

    `awsAccessKeyId`/`awsSecretAccessKey` are the old fields, typed into the
    node: they are still read so a saved workflow keeps working with the same
    identity, but a secret stored there is rejected on save and redacted on
    read (it is a secret key, like `password`).

    `credential_id` also accepts a Webhook Token — the old use of the field, which
    protects the download of the copy registered as an artifact. The server only
    injects the `s3` kind (and removes the id); any other id that arrives here is
    treated as that token.
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
                    # Injected by the server from the `s3` credential (see
                    # credential_resolver). Declared because `validate()`
                    # rebuilds the parameters from this list and would drop
                    # whatever was not in it. The UI hides it by name.
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
                # Applies only to the COPY registered as an artifact. The external
                # S3 bucket is a destination that whoever builds the workflow
                # configured explicitly, with its own credential — locality here
                # is about the platform's storage, not about where the user
                # decided to send their data.
                locality_property(
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
        # With the S3 credential resolved, the server has already removed the id; what
        # remains here is the Webhook Token that protects the registered copy (old use).
        credential_id = self.get_param('credential_id', '') or None

        # `credential_id` left over without `s3_auth`: the chosen credential was NOT
        # resolved (deleted, expired, of another kind, or private to someone who
        # did not trigger the run). Without a registered copy, this id cannot be the
        # Webhook Token of the old use — the server removes it in that case —, and
        # proceeding would do the upload with ANOTHER identity (the node's old keys
        # or the default boto3 chain on the executor), silently. Same rule as HttpRequest.
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
            # Same guard as the credential's connection test: an endpoint the
            # test would refuse does not become valid here.
            from flow.utils.geo_helpers import validate_url_ssrf
            await asyncio.to_thread(validate_url_ssrf, endpoint)

        if not bucket:
            raise ValueError("Parametro 'bucketName' e obrigatorio (ou um bucket padrao na credencial S3).")
        if not key:
            raise ValueError("Parametro 'key' e obrigatorio.")

        # Obtem o GeoDataFrame
        data = self.get_first_gdf(inputs)

        # Reprojects if needed. Stays OUTSIDE the try below: an invalid destination
        # CRS is not a serialization error, and the message would say otherwise.
        data = await asyncio.to_thread(ensure_gdf_crs, data, crs)

        features = len(data)
        logger.info(f"Serializando {features} feicoes para GeoJSON...")
        try:
            json_str = await asyncio.to_thread(gdf_para_geojson, data, nat_as_null=True)
        except Exception as e:
            raise RuntimeError(f"Erro ao serializar GeoDataFrame para GeoJSON: {e}") from e

        # Upload to external S3
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

        # Optional registration as an artifact in the internal MinIO
        if register_artifact:
            workspace_id, task_id = self.require_execution_context()

            if not label:
                label = os.path.splitext(os.path.basename(key))[0] or 's3_export'

            safe_label = slugify_label(label)
            filename = f"{safe_label}.geojson"
            content = json_str.encode('utf-8')

            localidade, quem = resolve_locality(self.get_param('localidade', None))
            if localidade == EXECUTOR:
                credential_id = None
            elif s3_auth and not credential_id:
                # `credential_id` was the S3 credential (the server injected it and
                # removed the id): no Webhook Token is left to protect the copy.
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
            self.log(describe_locality(localidade, quem))
            onde = 'neste executor' if localidade == EXECUTOR else 'no MinIO'
            self.log(f"Copia do artefato salva {onde}: {minio_key}")
            output_data['artifact_s3_key'] = minio_key
            result['__artifact__'] = artifact_meta

        result['output'] = output_data
        return result
