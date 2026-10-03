# app/schemas/agent_enrollment.py
"""
Pydantic schemas for the mTLS cert enrollment + renewal flow.

All with extra='forbid' — blocks unknown keys and limits the attack surface of
deeply nested payloads (D1 of the security report).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Admin: generates an OTP for an existing executor ───────────────────────────

class EnrollmentOTPResponse(BaseModel):
    """OTP generation response — the plaintext appears ONLY ONCE.

    It also carries the addresses the enrollment commands use, so the screen
    does not hard-code any: `server_url` is the executors' host (AGENTS_URL,
    empty when the installation neither configured it nor has a domain for the
    convention) and `public_url`, the site (FRONTEND_URL), from where install.sh
    is downloaded.
    """
    model_config = ConfigDict(extra="forbid")

    otp:        str
    expires_at: datetime
    executor_id:   str
    server_url: str = ""
    public_url: str = ""


# ── Executor: exchanges the OTP for a cert ─────────────────────────────────────

class EnrollRequest(BaseModel):
    """
    Body of POST /executores/enroll.

    Authentication via Authorization: Bearer {otp} — not included in the body.
    """
    model_config = ConfigDict(extra="forbid")

    csr_pem:        str = Field(..., min_length=1, max_length=8192, description="CSR em PEM (Ed25519)")
    public_key_pem: str = Field(..., min_length=1, max_length=2048, description="Chave publica X25519 (envelope encryption)")
    hostname:       str = Field(..., min_length=1, max_length=255)
    executor_version:  str = Field(..., min_length=1, max_length=20)
    os:             str = Field(..., min_length=1, max_length=64)


class EnrollResponse(BaseModel):
    """Cert bundle delivered to the executor after enrollment or renewal."""
    model_config = ConfigDict(extra="forbid")

    cert_pem:    str
    chain_pem:   str
    ca_pem:      str
    serial:      str
    fingerprint: str
    issued_at:   datetime
    expires_at:  datetime
    # Ed25519 public key with which the server signs jobs and commands. Delivered
    # HERE, inside the bundle already authenticated by the OTP (enroll) or by
    # mTLS (renew), so the executor pins it without going through any TOFU
    # window. Before, the executor fetched it with a separate GET on every
    # boot, without pinning — see executor/server_key.py. Optional for the case
    # where EXECUTOR_SIGNING_KEY is not configured on the server: the executor
    # handles its absence with its own message instead of receiving a
    # malformed bundle.
    server_signing_public_key: str | None = None


# ── Executor: renews the cert before expiry (authenticated by mTLS) ────────────

class RenewRequest(BaseModel):
    """
    Body of POST /executores/renew-cert. The executor's identity comes from mTLS.
    """
    model_config = ConfigDict(extra="forbid")

    csr_pem: str = Field(..., min_length=1, max_length=8192)
