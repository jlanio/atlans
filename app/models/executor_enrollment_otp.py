# app/models/executor_enrollment_otp.py
"""
Single-use OTP for enrolling executors via mTLS.

Flow:
  1. Admin creates the executor (status=pending) and generates an OTP via POST /executores/{id}/enroll-otp.
  2. The operator receives the OTP over a secure channel and runs `atlans-executor enroll --otp=...`.
  3. The executor exchanges the OTP for an mTLS cert via POST /executores/enroll.
  4. consumed_at is set atomically — the OTP cannot be reused.

We persist only the OTP's HMAC (otp_hash); the plaintext string appears only
once, in the response to the admin, and is never stored.
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
