# app/api/routers/auth_router.py
"""
Authentication endpoints — registration, login and JWT token renewal.

Brute-force protection:
  - Rate limit per IP (slowapi): 10 req/min on login
  - Lockout per username (Redis): 5 failed attempts → 15 min block
"""
import asyncio

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.auth import (
    UserCreate, UserLogin, Token, TokenRefresh, UserOut,
    ForgotPasswordRequest, ResetPasswordRequest,
    ResendVerificationRequest, MessageResponse,
)
from app.core.utils.jwt_utils import (
    verify_password, hash_password,
    create_access_token, create_refresh_token, decode_token,
    new_refresh_family, register_refresh_family,
    rotate_refresh_family, revoke_refresh_family, refresh_rate_exceeded,
)
from app.core.utils.logger import get_logger
from app.core.rate_limiter import limiter
from app.core.redis import contar_na_janela
from app.core import config
from app.core.config import FRONTEND_URL, EMAIL_VERIFY_TOKEN_TTL, PASSWORD_RESET_TOKEN_TTL
from app.services.email_service import send_email_background
from app.services.token_service import (
    create_email_verification_token, verify_email_token,
    create_password_reset_token, verify_password_reset_token,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def get_redis(request: Request) -> aioredis.Redis:
    """Returns the application's Redis pool (created in the lifespan)."""
    return request.app.state.redis


# ── Lockout settings ───────────────────────────────────────────────────────────
_MAX_ATTEMPTS   = 5        # failed attempts before the lockout
_LOCKOUT_TTL    = 15 * 60  # lockout seconds (15 min)
_ATTEMPTS_TTL   = 15 * 60  # counting window (resets along with the lockout)


async def _check_lockout(username: str, redis: aioredis.Redis) -> None:
    """Raises HTTP 429 if the user is locked out, with the remaining time."""
    locked = await redis.get(f"login_locked:{username}")
    if locked:
        ttl = await redis.ttl(f"login_locked:{username}")
        mins = (ttl + 59) // 60  # rounds up to minutes
        raise HTTPException(
            status_code=429,
            detail=f"Conta bloqueada por excesso de tentativas. Tente novamente em {mins} minuto(s).",
            headers={"Retry-After": str(ttl)},
        )


async def _record_failed(username: str, redis: aioredis.Redis) -> int:
    """Increments the failure counter. Locks the account on reaching the limit. Returns the remaining attempts."""
    attempts_key = f"login_failed:{username}"
    locked_key   = f"login_locked:{username}"

    # SLIDING window: each failure renews the deadline, and the counter only
    # resets after _ATTEMPTS_TTL without any failure.
    attempts, _ = await contar_na_janela(attempts_key, _ATTEMPTS_TTL, deslizante=True, redis=redis)

    if attempts >= _MAX_ATTEMPTS:
        await redis.setex(locked_key, _LOCKOUT_TTL, "1")
        await redis.delete(attempts_key)
        return 0

    return _MAX_ATTEMPTS - attempts


async def _clear_attempts(username: str, redis: aioredis.Redis) -> None:
    """Removes the counters after a successful login."""
    await redis.delete(f"login_failed:{username}", f"login_locked:{username}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

# Login and sign-up: 20/min per IP. The key is the public IP, and one IP can be
# a classroom, an office or a mobile carrier's entire CGNAT. While the counters
# lived in the memory of each of the 4 workers, the effective ceiling was
# already this (4 x 5); with them in Redis, 5/min would lock the group out.
# Brute force against ONE account is held off by the per-account lockout
# (_MAX_ATTEMPTS/_LOCKOUT_TTL).
_LIMITE_DE_ENTRADA_POR_IP = "20/minute"


@router.post("/register", response_model=UserOut, status_code=201, summary="Criar nova conta")
@limiter.limit(_LIMITE_DE_ENTRADA_POR_IP)
async def register(request: Request, payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # Checks username and email uniqueness with a unified message (avoids user enumeration)
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Usuário ou e-mail já em uso.")
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Usuário ou e-mail já em uso.")

    # bcrypt is CPU-bound (~200-300ms) and the lib releases the GIL: off the event
    # loop so it does not freeze WS heartbeats, live streaming and the worker's requests.
    hashed = await asyncio.to_thread(hash_password, payload.password)
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed,
    )
    db.add(user)
    await db.flush()  # generates user.id_hash without closing the transaction

    # Creates a default workspace for the new user
    default_ws = Workspace(
        name=f"Workspace de {user.username}",
        description="Workspace padrão",
        owner_id=user.id_hash,
        is_default=True,
    )
    db.add(default_ws)
    await db.flush()

    user.workspace_id = default_ws.id_hash

    await db.commit()
    await db.refresh(user)

    # Sends the verification email in the background
    token = await create_email_verification_token(user.id_hash)
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    send_email_background(
        to=user.email,
        subject="Confirme seu e-mail — Atlans",
        template="verify_email.html",
        context={
            "username": user.username,
            "verify_url": verify_url,
            "ttl_hours": EMAIL_VERIFY_TOKEN_TTL // 60,
        },
    )

    logger.info("Usuário '%s' registrado com sucesso.", user.username)
    return user


@router.post("/login", response_model=Token, summary="Autenticar e obter tokens JWT")
@limiter.limit(_LIMITE_DE_ENTRADA_POR_IP)
async def login(
    request: Request,
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    # The identifier may be an email or a username. Normalizes to lowercase: the
    # user lookup uses ident.lower(), so without normalizing here the lockout key
    # ('Admin' vs 'admin') differs from the real target and the per-account
    # lockout (defense against a distributed botnet) never fires — each case
    # variant is a separate bucket.
    ident = payload.identifier.strip().lower()

    # 1. Checks whether the account is locked out due to too many attempts
    await _check_lockout(ident, redis)

    # 2. Validates credentials — resolves by email (contains '@') or by username.
    # Emails are stored normalized (lowercase), so the comparison is direct and
    # uses the column's index.
    if "@" in ident:
        stmt = select(User).where(User.email == ident.lower())
    else:
        stmt = select(User).where(User.username == ident.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # bcrypt off the event loop (see register): under a login burst, the hashes
    # run in parallel instead of serializing and stalling the worker.
    senha_ok = bool(user) and await asyncio.to_thread(
        verify_password, payload.password, user.hashed_password,
    )
    if not senha_ok:
        remaining = await _record_failed(ident, redis)
        if remaining == 0:
            logger.warning("Conta '%s' bloqueada após %d tentativas falhas.", ident, _MAX_ATTEMPTS)
            raise HTTPException(
                status_code=429,
                detail="Conta bloqueada por excesso de tentativas. Tente novamente em 15 minuto(s).",
                headers={"Retry-After": str(_LOCKOUT_TTL)},
            )
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="Conta suspensa. Entre em contato com o administrador.")
    if user.status == "deleted":
        raise HTTPException(status_code=403, detail="Conta excluída.")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Conta desativada.")

    # Without an email transport the verification link never arrives: the
    # installation turns the requirement off with EXIGIR_EMAIL_VERIFICADO=false.
    if not user.email_verified and config.EXIGIR_EMAIL_VERIFICADO:
        raise HTTPException(
            status_code=403,
            detail="E-mail não verificado. Verifique sua caixa de entrada ou solicite um novo link.",
            headers={"X-Error-Code": "email_not_verified"},
        )

    # 3. Successful login — clears counters and updates last access
    await _clear_attempts(ident, redis)
    user.last_login_at = func.now()
    await db.commit()

    # Opens a new refresh token family for this session
    family, jti = new_refresh_family()
    await register_refresh_family(family, jti)

    data = {"sub": user.id_hash, "username": user.username, "family": family}
    logger.info("Login do usuário '%s'.", user.username)
    return Token(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token({**data, "jti": jti}),
    )


@router.post("/refresh", response_model=Token, summary="Renovar access token")
# No @limiter.limit: the per-IP limit turned the internal Next→API hop into a
# single platform-wide bucket. The real limit is per family, applied below after
# validating the token — see refresh_rate_exceeded in jwt_utils.
async def refresh_token(request: Request, payload: TokenRefresh, db: AsyncSession = Depends(get_db)):
    try:
        from app.core.utils.jwt_utils import AUDIENCE_REFRESH
        claims = decode_token(payload.refresh_token, expected_audience=AUDIENCE_REFRESH)
        if claims.get("type") != "refresh":
            raise ValueError("Token inválido")
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado.")

    family = claims.get("family")
    jti = claims.get("jti")
    if not family or not jti:
        # Token in the old format (no family) — no backward compat, forces re-login
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado.")

    # Limit per FAMILY (not per IP). 429 is TRANSIENT: the front end keeps the
    # session and retries shortly, instead of logging out.
    if await refresh_rate_exceeded(family):
        raise HTTPException(
            status_code=429,
            detail="Muitas renovações de sessão em sequência. Tente novamente em instantes.",
        )

    # Rotates the token; detects reuse (jti already rotated = theft)
    rot_status, new_jti = await rotate_refresh_family(family, jti)
    if rot_status != "ok":
        if rot_status == "reuse":
            logger.warning("Reuso de refresh token detectado — família '%s' revogada.", family)
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado.")

    result = await db.execute(select(User).where(User.id_hash == claims["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo.")

    data = {"sub": user.id_hash, "username": user.username, "family": family}
    return Token(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token({**data, "jti": new_jti}),
    )


@router.get("/me", response_model=UserOut, summary="Dados do usuário autenticado")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Email verification ────────────────────────────────────────────────────


@router.get("/verify-email", response_model=MessageResponse, summary="Verificar e-mail via token")
@limiter.limit("5/minute")
async def verify_email(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    user_id_hash = await verify_email_token(token)
    if not user_id_hash:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    result = await db.execute(select(User).where(User.id_hash == user_id_hash))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if user.email_verified:
        return MessageResponse(message="E-mail já verificado.")

    user.email_verified = True
    await db.commit()
    logger.info("E-mail do usuário '%s' verificado.", user.username)
    return MessageResponse(message="E-mail verificado com sucesso!")


@router.post("/resend-verification", response_model=MessageResponse, summary="Reenviar e-mail de verificação")
@limiter.limit("2/minute")
async def resend_verification(
    request: Request,
    payload: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    # Always a generic response (anti-enumeration)
    msg = MessageResponse(message="Se o e-mail estiver cadastrado e não verificado, um novo link será enviado.")

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or user.email_verified:
        return msg

    token = await create_email_verification_token(user.id_hash)
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    send_email_background(
        to=user.email,
        subject="Confirme seu e-mail — Atlans",
        template="verify_email.html",
        context={
            "username": user.username,
            "verify_url": verify_url,
            "ttl_hours": EMAIL_VERIFY_TOKEN_TTL // 60,
        },
    )
    return msg


# ── Password recovery ─────────────────────────────────────────────────────


@router.post("/forgot-password", response_model=MessageResponse, summary="Solicitar redefinição de senha")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # Always a generic response (anti-enumeration)
    msg = MessageResponse(message="Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha.")

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or user.status != "active":
        return msg

    token = await create_password_reset_token(user.id_hash)
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    send_email_background(
        to=user.email,
        subject="Redefinir senha — Atlans",
        template="password_reset.html",
        context={
            "username": user.username,
            "reset_url": reset_url,
            "ttl_minutes": PASSWORD_RESET_TOKEN_TTL,
        },
    )
    return msg


@router.post("/reset-password", response_model=MessageResponse, summary="Redefinir senha via token")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    user_id_hash = await verify_password_reset_token(payload.token)
    if not user_id_hash:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    result = await db.execute(select(User).where(User.id_hash == user_id_hash))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    user.hashed_password = await asyncio.to_thread(hash_password, payload.password)
    # Cascade: whoever resets the password (possibly because the account was
    # compromised) does not want any agent staying authenticated with an old
    # token. Same transaction as the commit below.
    from app.services.api_token_service import revogar_todos_do_usuario

    await revogar_todos_do_usuario(db, [user.id_hash], motivo="password_reset")
    await db.commit()
    logger.info("Senha do usuário '%s' redefinida.", user.username)
    return MessageResponse(message="Senha redefinida com sucesso!")


@router.post("/logout", response_model=MessageResponse, summary="Revogar token de acesso")
async def logout(
    request: Request,
    current_user=Depends(get_current_user),
):
    """Revokes the access token (blacklist) and the session's refresh token family."""
    from app.core.utils.jwt_utils import blacklist_token

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ").strip()
        await blacklist_token(token)
        # Revokes the whole refresh token family (really ends the session).
        # The access token carries the 'family' claim mirrored from the associated refresh.
        try:
            from app.core.utils.jwt_utils import AUDIENCE_ACCESS
            family = decode_token(token, expected_audience=AUDIENCE_ACCESS).get("family")
            if family:
                await revoke_refresh_family(family)
        except Exception:
            # Token expired or invalid — the blacklist was already done above; OK.
            pass
    return MessageResponse(message="Logout realizado com sucesso.")
