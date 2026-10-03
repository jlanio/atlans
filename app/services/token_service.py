# app/services/token_service.py
"""
Opaque token service for email verification and password reset.

Tokens are stored in Redis with automatic TTL.
Each token is single-use — consumed on the first validation.
"""
import secrets

from app.core.config import EMAIL_VERIFY_TOKEN_TTL, PASSWORD_RESET_TOKEN_TTL
from app.core.redis import get_redis_pool


# ── Email verification ─────────────────────────────────────────────────────


async def create_email_verification_token(user_id_hash: str) -> str:
    """Generates an email verification token and stores it in Redis with a TTL."""
    token = secrets.token_urlsafe(32)
    redis = get_redis_pool()
    await redis.setex(
        f"email_verify:{token}",
        EMAIL_VERIFY_TOKEN_TTL * 60,
        user_id_hash,
    )
    return token


async def verify_email_token(token: str) -> str | None:
    """Validates and consumes the token. Returns user_id_hash or None if invalid/expired."""
    redis = get_redis_pool()
    user_id = await redis.get(f"email_verify:{token}")
    if user_id:
        await redis.delete(f"email_verify:{token}")
    return user_id


# ── Password reset ─────────────────────────────────────────────────────────


async def create_password_reset_token(user_id_hash: str) -> str:
    """Generates a password reset token. Invalidates the same user's previous token."""
    token = secrets.token_urlsafe(32)
    ttl = PASSWORD_RESET_TOKEN_TTL * 60
    redis = get_redis_pool()

    # Invalidates this user's previous token (only the latest link works)
    prev = await redis.get(f"pwd_reset_user:{user_id_hash}")
    if prev:
        await redis.delete(f"pwd_reset:{prev}")

    await redis.setex(f"pwd_reset:{token}", ttl, user_id_hash)
    await redis.setex(f"pwd_reset_user:{user_id_hash}", ttl, token)
    return token


async def verify_password_reset_token(token: str) -> str | None:
    """Validates and consumes the reset token. Returns user_id_hash or None."""
    redis = get_redis_pool()
    user_id = await redis.get(f"pwd_reset:{token}")
    if user_id:
        await redis.delete(f"pwd_reset:{token}")
        await redis.delete(f"pwd_reset_user:{user_id}")
    return user_id
