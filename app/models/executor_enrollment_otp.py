# app/models/executor_enrollment_otp.py
"""
OTP de uso unico para enrollment de executores via mTLS.

Fluxo:
  1. Admin cria executor (status=pending) e gera OTP via POST /executores/{id}/enroll-otp.
  2. Operador rece o OTP por canal seguro e roda `atlans-executor enroll --otp=...`.
  3. Executor troca OTP por cert mTLS via POST /executores/enroll.
  4. consumed_at marcado atomicamente — OTP nao pode ser reutilizado.

Persistimos apenas HMAC do OTP (otp_hash); a string plaintext aparece uma
unica vez na resposta ao admin e nunca e armazenada.
"""
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, func

from app.models.base import Base


class ExecutorEnrollmentOTP(Base):
    __tablename__ = "executor_enrollment_otp"

    id_hash = Column(
        String(36), primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Nome SQL "executor_id" (renomeada em 20260716_0001); atributo Python
    # mantido como executor_id ate R2.3 renomear identificadores.
    executor_id = Column(
        "executor_id",
        String(36),
        ForeignKey("executors.id_hash", ondelete="CASCADE"),
        nullable=False,
    )

    # HMAC-SHA256(otp_plaintext, OTP_PEPPER) em hex — 64 chars.
    # Lookup O(1) via index parcial (apenas linhas com consumed_at IS NULL).
    otp_hash = Column(String(64), nullable=False, unique=True)

    expires_at       = Column(DateTime, nullable=False)
    consumed_at      = Column(DateTime, nullable=True)
    consumed_from_ip = Column(String(45), nullable=True)

    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
