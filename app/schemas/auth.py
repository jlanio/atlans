# app/schemas/auth.py
import re
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional

_USERNAME_RE = re.compile(r"^[a-z0-9_]+$")


def _normalize_email(value: str) -> str:
    """Canoniza e-mail para minúsculas + sem espaços nas bordas.

    Garante que a constraint unique (case-sensitive no Postgres) não permita
    contas duplicadas variando apenas a caixa (Joao@x.com vs joao@x.com).
    """
    return value.strip().lower()


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário único (letras minúsculas, números e _)")
    email: EmailStr
    password: str = Field(..., min_length=8, description="Senha (mínimo 8 caracteres)")
    password_confirm: Optional[str] = Field(None, description="Confirmação de senha — deve ser igual a password")
    workspace_id: Optional[str] = None

    _norm_email = field_validator("email")(lambda cls, v: _normalize_email(v))

    @model_validator(mode="after")
    def validate_fields(self) -> "UserCreate":
        # Valida formato do username: apenas letras minúsculas, números e underscore
        if not _USERNAME_RE.match(self.username):
            raise ValueError("O nome de usuário só pode conter letras minúsculas, números e underscore (_).")
        # Valida confirmação de senha, se fornecida
        if self.password_confirm is not None and self.password != self.password_confirm:
            raise ValueError("As senhas não coincidem.")
        return self


class UserLogin(BaseModel):
    identifier: str = Field(..., description="E-mail ou nome de usuário")
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id_hash: str
    username: str
    email: str
    is_active: bool
    email_verified: bool = False
    status: str = "active"
    role: str = "user"
    agent_quota: int = 0
    workspace_id: Optional[str] = None

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    _norm_email = field_validator("email")(lambda cls, v: _normalize_email(v))


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8, description="Nova senha (mínimo 8 caracteres)")
    password_confirm: str = Field(..., min_length=8, description="Confirmação da nova senha")

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.password != self.password_confirm:
            raise ValueError("As senhas não coincidem.")
        return self


class ResendVerificationRequest(BaseModel):
    email: EmailStr

    _norm_email = field_validator("email")(lambda cls, v: _normalize_email(v))


class MessageResponse(BaseModel):
    message: str
