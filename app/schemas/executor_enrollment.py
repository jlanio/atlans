# app/schemas/agent_enrollment.py
"""
Schemas Pydantic para o fluxo de enrollment + renewal de cert mTLS.

Todos com extra='forbid' — bloqueia keys desconhecidos e limita superficie de
ataque por payload aninhado profundo (D1 do relatorio de seguranca).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Admin: gera OTP para executor ja existente ─────────────────────────────────

class EnrollmentOTPResponse(BaseModel):
    """Resposta da geracao de OTP — plaintext aparece UMA UNICA VEZ.

    Leva tambem os enderecos que os comandos de matricula usam, para a tela nao
    trazer nenhum fixo: `server_url` e o host dos executores (AGENTS_URL, vazio
    quando a instalacao nao o configurou nem tem dominio para a convencao) e
    `public_url`, o site (FRONTEND_URL), de onde o install.sh e baixado.
    """
    model_config = ConfigDict(extra="forbid")

    otp:        str
    expires_at: datetime
    executor_id:   str
    server_url: str = ""
    public_url: str = ""


# ── Executor: troca OTP por cert ───────────────────────────────────────────────

class EnrollRequest(BaseModel):
    """
    Corpo do POST /executores/enroll.

    Autenticacao via Authorization: Bearer {otp} — nao incluido no body.
    """
    model_config = ConfigDict(extra="forbid")

    csr_pem:        str = Field(..., min_length=1, max_length=8192, description="CSR em PEM (Ed25519)")
    public_key_pem: str = Field(..., min_length=1, max_length=2048, description="Chave publica X25519 (envelope encryption)")
    hostname:       str = Field(..., min_length=1, max_length=255)
    executor_version:  str = Field(..., min_length=1, max_length=20)
    os:             str = Field(..., min_length=1, max_length=64)


class EnrollResponse(BaseModel):
    """Cert bundle entregue ao executor apos enrollment ou renewal."""
    model_config = ConfigDict(extra="forbid")

    cert_pem:    str
    chain_pem:   str
    ca_pem:      str
    serial:      str
    fingerprint: str
    issued_at:   datetime
    expires_at:  datetime
    # Chave publica Ed25519 com que o servidor assina jobs e comandos. Entregue
    # AQUI, dentro do bundle ja autenticado pelo OTP (enroll) ou pelo mTLS
    # (renew), para que o executor a fixe sem passar por nenhuma janela de TOFU.
    # Antes o executor a buscava num GET separado a cada boot, sem pinning —
    # ver executor/server_key.py. Opcional para o caso de EXECUTOR_SIGNING_KEY
    # nao estar configurada no servidor: o executor trata a ausencia com
    # mensagem propria em vez de receber um bundle malformado.
    server_signing_public_key: str | None = None


# ── Executor: renova cert antes do vencimento (autenticado por mTLS) ───────────

class RenewRequest(BaseModel):
    """
    Corpo do POST /executores/renew-cert. Identidade do executor vem do mTLS.
    """
    model_config = ConfigDict(extra="forbid")

    csr_pem: str = Field(..., min_length=1, max_length=8192)
