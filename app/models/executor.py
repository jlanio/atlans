# app/models/executor.py
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class Executor(Base):
    """
    External executor registered in the system.

    Lifecycle:
      pending  → admin created the executor; OTP generated for enrollment
      active   → executor enrolled, received an mTLS cert and registered its X25519 public_key
      inactive → manually deactivated
      revoked  → cert revoked, reconnection blocked via blacklist
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

    # True for executors in the platform's default pool (multiple allowed)
    is_default = Column(Boolean, nullable=False, server_default="false")

    # "pending" | "active" | "inactive" | "revoked"
    status = Column(String(20), nullable=False, server_default="pending")

    # The executor's X25519 public key (envelope encryption of jobs).
    # Registered at enrollment from the CSR.
    public_key = Column(Text, nullable=True)

    # Tracking of the mTLS cert issued by the internal CA (step-ca).
    # Identifies the current credential; the serial changes on every renew/re-enroll.
    cert_serial             = Column(String(64), nullable=True, unique=True)
    cert_fingerprint_sha256 = Column(String(64), nullable=True)
    cert_issued_at          = Column(DateTime, nullable=True)
    cert_expires_at         = Column(DateTime, nullable=True)

    # List of capabilities declared by the executor: ["run_workflow", "read_postgis", …]
    capabilities = Column(JSONB, nullable=False, server_default="[]")

    # Parallelism limits — used for back-pressure in dispatch
    max_concurrent_jobs = Column(Integer, nullable=False, server_default="4")
    max_queue_size       = Column(Integer, nullable=False, server_default="50")

    # Executor software version (sent in the WebSocket handshake)
    # SQL name "executor_version" (renamed in 20260716_0001); Python
    # attribute kept as executor_version until R2.3.
    executor_version = Column("executor_version", String(20), nullable=True)

    # Executor hardware info (CPU, RAM, disk, OS) — sent in the handshake
    system_info = Column(JSONB, nullable=True)

    last_seen_at = Column(DateTime, nullable=True)
    created_by   = Column(String(36), nullable=True, index=True)  # User.id_hash
    created_at   = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Soft delete: filled in by delete_agent(); deleted executors are hidden from listings
    deleted_at = Column(DateTime, nullable=True, index=True)
