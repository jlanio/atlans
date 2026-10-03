"""
Credential type schemas.

Each entry declares the fields the type needs, with label, placeholder,
input type and whether it is required. The frontend uses this to render guided
forms — without the user needing to know the key names.
"""

from typing import List, Optional
from pydantic import BaseModel


class CredentialFieldSchema(BaseModel):
    key: str
    label: str
    # "text" | "password" | "number" | "select"
    type: str = "text"
    required: bool = True
    placeholder: str = ""
    default: Optional[str] = None
    options: Optional[List[str]] = None
    description: Optional[str] = None


class CredentialTypeSchema(BaseModel):
    type: str
    label: str
    description: str
    # Node types (categories) that accept this credential
    node_types: List[str]
    fields: List[CredentialFieldSchema]


CREDENTIAL_TYPE_SCHEMAS: dict[str, CredentialTypeSchema] = {
    "postgresql": CredentialTypeSchema(
        type="postgresql",
        label="PostgreSQL / PostGIS",
        description="Conexão com banco de dados PostgreSQL ou PostGIS",
        node_types=["datasource", "output"],
        fields=[
            CredentialFieldSchema(key="host", label="Host", type="text", placeholder="localhost"),
            CredentialFieldSchema(key="port", label="Porta", type="number", placeholder="5432", default="5432", required=False),
            CredentialFieldSchema(key="database", label="Banco de dados", type="text", placeholder="mydb"),
            CredentialFieldSchema(key="user", label="Usuário", type="text", placeholder="postgres"),
            CredentialFieldSchema(key="password", label="Senha", type="password"),
        ],
    ),
    "mysql": CredentialTypeSchema(
        type="mysql",
        label="MySQL / MariaDB",
        description="Conexão com banco de dados MySQL ou MariaDB",
        node_types=["datasource", "output"],
        fields=[
            CredentialFieldSchema(key="host", label="Host", type="text", placeholder="localhost"),
            CredentialFieldSchema(key="port", label="Porta", type="number", placeholder="3306", default="3306", required=False),
            CredentialFieldSchema(key="database", label="Banco de dados", type="text", placeholder="mydb"),
            CredentialFieldSchema(key="user", label="Usuário", type="text", placeholder="root"),
            CredentialFieldSchema(key="password", label="Senha", type="password"),
        ],
    ),
    "s3": CredentialTypeSchema(
        type="s3",
        label="Amazon S3",
        description="Credenciais de acesso ao Amazon S3 ou compatíveis (MinIO, etc.)",
        node_types=["output"],
        fields=[
            CredentialFieldSchema(key="access_key_id", label="Access Key ID", type="text"),
            CredentialFieldSchema(key="secret_access_key", label="Secret Access Key", type="password"),
            CredentialFieldSchema(key="region", label="Região", type="text", placeholder="us-east-1"),
            CredentialFieldSchema(
                key="bucket",
                label="Bucket padrão",
                type="text",
                required=False,
                description="Pode ser sobrescrito no nó",
            ),
            CredentialFieldSchema(
                key="endpoint_url",
                label="Endpoint URL (MinIO/S3-compatível)",
                type="text",
                required=False,
                placeholder="http://minio:9000",
                description="Deixe vazio para usar a AWS padrão",
            ),
        ],
    ),
    "http_bearer": CredentialTypeSchema(
        type="http_bearer",
        label="HTTP Bearer Token",
        description="Token para autenticação Bearer em APIs REST",
        node_types=["action"],
        fields=[
            CredentialFieldSchema(key="token", label="Token", type="password"),
        ],
    ),
    "http_basic": CredentialTypeSchema(
        type="http_basic",
        label="HTTP Basic Auth",
        description="Usuário e senha para autenticação Basic em APIs REST",
        node_types=["action"],
        fields=[
            CredentialFieldSchema(key="username", label="Usuário", type="text"),
            CredentialFieldSchema(key="password", label="Senha", type="password"),
        ],
    ),
    "webhook_token": CredentialTypeSchema(
        type="webhook_token",
        label="Webhook Token",
        description="Token secreto para proteger triggers do tipo Webhook",
        node_types=["trigger"],
        fields=[
            CredentialFieldSchema(key="token", label="Token secreto", type="password"),
            CredentialFieldSchema(
                key="expires_at",
                label="Expiração (ISO 8601)",
                type="text",
                required=False,
                placeholder="2026-12-31T23:59:59Z",
                description="Opcional. Deixe vazio para token sem expiração",
            ),
        ],
    ),
    "smtp": CredentialTypeSchema(
        type="smtp",
        label="SMTP (E-mail)",
        description="Configurações de servidor de e-mail para envio de mensagens",
        node_types=["output"],
        fields=[
            CredentialFieldSchema(key="host", label="Host SMTP", type="text", placeholder="smtp.gmail.com"),
            CredentialFieldSchema(key="port", label="Porta", type="number", placeholder="587", default="587", required=False),
            CredentialFieldSchema(key="username", label="Usuário / E-mail", type="text"),
            CredentialFieldSchema(key="password", label="Senha / App Password", type="password"),
            CredentialFieldSchema(
                key="use_tls",
                label="Usar TLS",
                type="select",
                options=["true", "false"],
                default="true",
                required=False,
            ),
        ],
    ),
    "wfs": CredentialTypeSchema(
        type="wfs",
        label="WFS (Web Feature Service)",
        description="Usuário e senha (HTTP Basic) para serviços WFS protegidos",
        node_types=["datasource"],
        fields=[
            CredentialFieldSchema(key="username", label="Usuário", type="text"),
            CredentialFieldSchema(key="password", label="Senha", type="password"),
        ],
    ),
    # GeoServer's authkey module: one key per user, sent with every
    # request. `parameter` and `location` have defaults, but the screen only DISPLAYS the
    # default (it does not write it to `data`) — the consumer applies the default on its own.
    "geoserver_authkey": CredentialTypeSchema(
        type="geoserver_authkey",
        label="GeoServer (authkey)",
        description="Chave do módulo authkey do GeoServer, enviada pelo nó WFS em cada requisição",
        node_types=["datasource"],
        fields=[
            CredentialFieldSchema(key="token", label="Chave (authkey)", type="password"),
            CredentialFieldSchema(
                key="parameter",
                label="Nome do parâmetro",
                type="text",
                required=False,
                default="authkey",
                placeholder="authkey",
                description="O nome configurado no filtro authkey do GeoServer — quase sempre 'authkey'.",
            ),
            CredentialFieldSchema(
                key="location",
                label="Enviar a chave como",
                type="select",
                required=False,
                options=["url", "header"],
                default="url",
                description="url: ?authkey=… em cada requisição (o padrão do GeoServer); "
                            "header: um cabeçalho HTTP com o nome acima.",
            ),
        ],
    ),
}
