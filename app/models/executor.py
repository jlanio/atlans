# app/models/executor.py
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class Executor(Base):
    """
    Executor externo registrado no sistema.

    Ciclo de vida:
      pending  → admin criou executor; OTP gerado para enrollment
      active   → executor fez enroll, recebeu cert mTLS e public_key X25519 registrada
      inactive → desativado manualmente
      revoked  → cert revogado, reconexao bloqueada via blacklist
    """
    __tablename__ = "executors"

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(
        String(36), unique=True, nullable=False,
        default=lambda: str(uuid4()), index=True,
    )

    name        = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)

    # "default" | "dedicated"
    # Nome SQL "executor_type" (renomeada em 20260716_0001); atributo Python
    # mantido como executor_type ate R2.3 renomear identificadores.
    executor_type = Column("executor_type", String(20), nullable=False, server_default="dedicated")

    # True para executores do pool padrão da plataforma (múltiplos permitidos)
    is_default = Column(Boolean, nullable=False, server_default="false")

    # "pending" | "active" | "inactive" | "revoked"
    status = Column(String(20), nullable=False, server_default="pending")

    # Chave pública X25519 do executor (envelope encryption de jobs).
    # Registrada no enrollment a partir do CSR.
    public_key = Column(Text, nullable=True)

    # Tracking do cert mTLS emitido pela CA interna (step-ca).
    # Identifica a credencial atual; serial muda a cada renew/re-enroll.
    cert_serial             = Column(String(64), nullable=True, unique=True)
    cert_fingerprint_sha256 = Column(String(64), nullable=True)
    cert_issued_at          = Column(DateTime, nullable=True)
    cert_expires_at         = Column(DateTime, nullable=True)

    # Lista de capacidades declaradas pelo executor: ["run_workflow", "read_postgis", …]
    capabilities = Column(JSONB, nullable=False, server_default="[]")

    # Limites de paralelismo — usados para back-pressure no dispatch
    max_concurrent_jobs = Column(Integer, nullable=False, server_default="4")
    max_queue_size       = Column(Integer, nullable=False, server_default="50")

    # Versão do software do executor (enviada no handshake do WebSocket)
    # Nome SQL "executor_version" (renomeada em 20260716_0001); atributo
    # Python mantido como executor_version ate R2.3.
    executor_version = Column("executor_version", String(20), nullable=True)

    # Info de hardware do executor (CPU, RAM, disco, OS) — enviada no handshake
    system_info = Column(JSONB, nullable=True)

    last_seen_at = Column(DateTime, nullable=True)
    created_by   = Column(String(36), nullable=True, index=True)  # User.id_hash
    created_at   = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Soft-delete: preenchido por delete_agent(); executores deletados são ocultados das listagens
    deleted_at = Column(DateTime, nullable=True, index=True)
