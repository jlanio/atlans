# models/credential.py
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4

from app.models.base import Base
from app.core.utils.encryption import encrypt_string

class Credential(Base):
    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # id_hash: identificador público consistente com demais entidades (Workflow, Schedule, etc.)
    # Derivado do UUID primário — mantém compatibilidade com rotas existentes que usam UUID.
    id_hash = Column(String(36), unique=True, nullable=False, index=True,
                     default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # ex: "postgresql", "webhook_token", etc.
    data = Column(JSONB, nullable=False)   # Encrypted key-value data
    owner_id = Column(String(36), nullable=True, index=True)   # User.id_hash do criador
    # workspace_id: quando preenchido, a credencial é COMPARTILHADA — visível para
    # todos os membros daquele workspace, não só para o dono. NULL = credencial
    # privada do dono (comportamento legado). Ver credential_service.list_* e
    # credential_loader.resolve_credentials_from_ids.
    workspace_id = Column(String(36), nullable=True, index=True)
    # Metadados organizacionais, não-secretos — por isso são colunas próprias e
    # não entram em `data` (que é cifrado por encrypt_and_store).
    description = Column(String, nullable=True)
    tags = Column(JSONB, nullable=True)   # lista de strings
    # Última vez que a credencial foi RESOLVIDA para execução. Escrito best-effort
    # pelo resolver (credential_loader); nunca é caminho crítico.
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def expires_at(self) -> Optional[datetime]:
        """Expiração derivada de `data['expires_at']` — não é coluna.

        A expiração sempre viveu dentro do JSONB `data` (texto puro; o
        encrypt_and_store nunca cifra essa chave), e é de lá que o resolver a
        aplica. Uma coluna paralela seria uma segunda fonte de verdade que o
        resolver ignoraria. Expor como property mantém uma fonte só e ainda faz
        o Pydantic (from_attributes) preencher CredentialOut.expires_at — o selo
        de expiração na UI dependia disso e vinha sempre nulo.

        Devolve None quando ausente ou mal formado; validar/recusar é papel de
        quem escreve, não de quem lê para exibir.
        """
        raw = (self.data or {}).get("expires_at")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def encrypt_and_store(self, plain_data: dict):
        for k, v in plain_data.items():
            # ✅ validação: expires_at deve ser string ISO 8601
            if k == "expires_at" and v:
                try:
                    datetime.fromisoformat(v.replace("Z", "+00:00"))
                except ValueError:
                    raise ValueError("O campo 'expires_at' deve estar em formato ISO 8601.")

        # Auditoria (SEG-19): NÃO pular a cifragem por prefixo "gAAAA". Os
        # caminhos legítimos (create/update) sempre passam TEXTO CLARO aqui — o
        # update decifra o blob atual, mescla e recifra. O único jeito de um
        # valor chegar já com "gAAAA" era o cliente ENVIAR o texto cifrado de
        # outra pessoa: sem a cifragem, ele ficava gravado como estava e o
        # GET /credentials/{id}/data o decifrava com a chave da plataforma —
        # um oráculo que transformava "tenho o ciphertext" em "tenho o segredo".
        # Cifrar sempre faz um "gAAAA" enviado virar ciphertext de si mesmo:
        # decifrar devolve a string "gAAAA…", nunca o segredo alheio.
        self.data = {
            k: encrypt_string(v)
            if isinstance(v, str) and k != "expires_at"  # expires_at NÃO é cifrado
            else v
            for k, v in plain_data.items()
        }
