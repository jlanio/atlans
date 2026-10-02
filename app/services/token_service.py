# app/services/token_service.py
"""
Serviço de tokens opacos para verificação de email e reset de senha.

Tokens são armazenados em Redis com TTL automático.
Cada token é de uso único — consumido na primeira validação.
"""
import secrets

from app.core.config import EMAIL_VERIFY_TOKEN_TTL, PASSWORD_RESET_TOKEN_TTL
from app.core.redis import get_redis_pool


# ── Verificação de email ───────────────────────────────────────────────────


async def create_email_verification_token(user_id_hash: str) -> str:
    """Gera token de verificação de email e armazena em Redis com TTL."""
    token = secrets.token_urlsafe(32)
    redis = get_redis_pool()
    await redis.setex(
        f"email_verify:{token}",
        EMAIL_VERIFY_TOKEN_TTL * 60,
        user_id_hash,
    )
    return token


async def verify_email_token(token: str) -> str | None:
    """Valida e consome token. Retorna user_id_hash ou None se inválido/expirado."""
    redis = get_redis_pool()
    user_id = await redis.get(f"email_verify:{token}")
    if user_id:
        await redis.delete(f"email_verify:{token}")
    return user_id


# ── Reset de senha ─────────────────────────────────────────────────────────


async def create_password_reset_token(user_id_hash: str) -> str:
    """Gera token de reset de senha. Invalida token anterior do mesmo usuário."""
    token = secrets.token_urlsafe(32)
    ttl = PASSWORD_RESET_TOKEN_TTL * 60
    redis = get_redis_pool()

    # Invalida token anterior deste usuário (apenas o último link funciona)
    prev = await redis.get(f"pwd_reset_user:{user_id_hash}")
    if prev:
        await redis.delete(f"pwd_reset:{prev}")

    await redis.setex(f"pwd_reset:{token}", ttl, user_id_hash)
    await redis.setex(f"pwd_reset_user:{user_id_hash}", ttl, token)
    return token


async def verify_password_reset_token(token: str) -> str | None:
    """Valida e consome token de reset. Retorna user_id_hash ou None."""
    redis = get_redis_pool()
    user_id = await redis.get(f"pwd_reset:{token}")
    if user_id:
        await redis.delete(f"pwd_reset:{token}")
        await redis.delete(f"pwd_reset_user:{user_id}")
    return user_id
