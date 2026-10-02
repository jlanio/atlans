# app/api/routers/auth_router.py
"""
Endpoints de autenticação — registro, login e renovação de token JWT.

Proteção contra brute-force:
  - Rate limit por IP (slowapi): 10 req/min no login
  - Lockout por username (Redis): 5 tentativas falhas → bloqueio de 15 min
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
    """Retorna o pool Redis da aplicação (criado no lifespan)."""
    return request.app.state.redis


# ── Configurações de lockout ───────────────────────────────────────────────────
_MAX_ATTEMPTS   = 5        # tentativas falhas antes do bloqueio
_LOCKOUT_TTL    = 15 * 60  # segundos de bloqueio (15 min)
_ATTEMPTS_TTL   = 15 * 60  # janela de contagem (reseta junto com o lockout)


async def _check_lockout(username: str, redis: aioredis.Redis) -> None:
    """Lança HTTP 429 se o usuário está bloqueado, com tempo restante."""
    locked = await redis.get(f"login_locked:{username}")
    if locked:
        ttl = await redis.ttl(f"login_locked:{username}")
        mins = (ttl + 59) // 60  # arredonda para cima em minutos
        raise HTTPException(
            status_code=429,
            detail=f"Conta bloqueada por excesso de tentativas. Tente novamente em {mins} minuto(s).",
            headers={"Retry-After": str(ttl)},
        )


async def _record_failed(username: str, redis: aioredis.Redis) -> int:
    """Incrementa contador de falhas. Bloqueia conta ao atingir o limite. Retorna tentativas restantes."""
    attempts_key = f"login_failed:{username}"
    locked_key   = f"login_locked:{username}"

    # Janela DESLIZANTE: cada falha renova o prazo, e o contador só zera depois
    # de _ATTEMPTS_TTL sem falha nenhuma.
    attempts, _ = await contar_na_janela(attempts_key, _ATTEMPTS_TTL, deslizante=True, redis=redis)

    if attempts >= _MAX_ATTEMPTS:
        await redis.setex(locked_key, _LOCKOUT_TTL, "1")
        await redis.delete(attempts_key)
        return 0

    return _MAX_ATTEMPTS - attempts


async def _clear_attempts(username: str, redis: aioredis.Redis) -> None:
    """Remove contadores após login bem-sucedido."""
    await redis.delete(f"login_failed:{username}", f"login_locked:{username}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

# Login e cadastro: 20/min por IP. A chave e o IP publico, e um IP pode ser
# uma turma, um escritorio ou um CGNAT de operadora movel inteiro. Enquanto os
# contadores viviam na memoria de cada um dos 4 workers, o teto efetivo ja era
# esse (4 x 5); com eles no Redis, 5/min trancaria o grupo. Forca bruta contra
# UMA conta e o bloqueio por conta (_MAX_ATTEMPTS/_LOCKOUT_TTL) que segura.
_LIMITE_DE_ENTRADA_POR_IP = "20/minute"


@router.post("/register", response_model=UserOut, status_code=201, summary="Criar nova conta")
@limiter.limit(_LIMITE_DE_ENTRADA_POR_IP)
async def register(request: Request, payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # Verifica unicidade de username e email com mensagem unificada (evita user enumeration)
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Usuário ou e-mail já em uso.")
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Usuário ou e-mail já em uso.")

    # bcrypt é CPU-bound (~200-300ms) e a lib libera a GIL: fora do event loop
    # para não congelar heartbeats WS, streaming ao vivo e requests do worker.
    hashed = await asyncio.to_thread(hash_password, payload.password)
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed,
    )
    db.add(user)
    await db.flush()  # gera user.id_hash sem fechar a transação

    # Cria workspace padrão para o novo usuário
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

    # Envia email de verificação em background
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
    # O identificador pode ser e-mail ou username. Normaliza para lowercase: a
    # busca do usuario usa ident.lower(), entao sem normalizar aqui a chave de
    # lockout ('Admin' vs 'admin') difere do alvo real e o bloqueio por conta
    # (defesa contra botnet distribuido) nunca dispara — cada variante de caixa
    # e um balde separado.
    ident = payload.identifier.strip().lower()

    # 1. Verifica se a conta está bloqueada por excesso de tentativas
    await _check_lockout(ident, redis)

    # 2. Valida credenciais — resolve por e-mail (contém '@') ou por username.
    # E-mails são armazenados normalizados (lowercase), então a comparação é
    # direta e aproveita o índice da coluna.
    if "@" in ident:
        stmt = select(User).where(User.email == ident.lower())
    else:
        stmt = select(User).where(User.username == ident.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # bcrypt fora do event loop (ver register): sob rajada de login, os hashes
    # passam a rodar em paralelo em vez de serializar e travar o worker.
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

    # Sem transporte de e-mail o link de verificacao nunca chega: a instalacao
    # desliga a exigencia com EXIGIR_EMAIL_VERIFICADO=false.
    if not user.email_verified and config.EXIGIR_EMAIL_VERIFICADO:
        raise HTTPException(
            status_code=403,
            detail="E-mail não verificado. Verifique sua caixa de entrada ou solicite um novo link.",
            headers={"X-Error-Code": "email_not_verified"},
        )

    # 3. Login bem-sucedido — limpa contadores e atualiza último acesso
    await _clear_attempts(ident, redis)
    user.last_login_at = func.now()
    await db.commit()

    # Abre uma nova família de refresh tokens para esta sessão
    family, jti = new_refresh_family()
    await register_refresh_family(family, jti)

    data = {"sub": user.id_hash, "username": user.username, "family": family}
    logger.info("Login do usuário '%s'.", user.username)
    return Token(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token({**data, "jti": jti}),
    )


@router.post("/refresh", response_model=Token, summary="Renovar access token")
# Sem @limiter.limit: o limite por IP transformava o hop interno Next→API num
# balde único de plataforma. O limite real é por família, aplicado abaixo após
# validar o token — ver refresh_rate_exceeded em jwt_utils.
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
        # Token em formato antigo (sem família) — sem retrocompat, força re-login
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado.")

    # Limite por FAMÍLIA (não por IP). 429 é TRANSITÓRIO: o front mantém a sessão
    # e tenta de novo em instantes, em vez de deslogar.
    if await refresh_rate_exceeded(family):
        raise HTTPException(
            status_code=429,
            detail="Muitas renovações de sessão em sequência. Tente novamente em instantes.",
        )

    # Rotaciona o token; detecta reuso (jti já rotacionado = roubo)
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


# ── Verificação de email ──────────────────────────────────────────────────


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
    # Resposta genérica sempre (anti-enumeração)
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


# ── Recuperação de senha ──────────────────────────────────────────────────


@router.post("/forgot-password", response_model=MessageResponse, summary="Solicitar redefinição de senha")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # Resposta genérica sempre (anti-enumeração)
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
    # Cascata: quem redefine a senha (possivelmente porque a conta foi
    # comprometida) não quer nenhum agente seguindo autenticado com um token
    # antigo. Mesma transação do commit abaixo.
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
    """Revoga o access token (blacklist) e a família de refresh tokens da sessão."""
    from app.core.utils.jwt_utils import blacklist_token

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ").strip()
        await blacklist_token(token)
        # Revoga toda a família de refresh tokens (encerra a sessão de verdade).
        # O access token carrega o claim 'family' espelhado do refresh associado.
        try:
            from app.core.utils.jwt_utils import AUDIENCE_ACCESS
            family = decode_token(token, expected_audience=AUDIENCE_ACCESS).get("family")
            if family:
                await revoke_refresh_family(family)
        except Exception:
            # Token expirado ou invalido — blacklist ja foi feita acima; OK.
            pass
    return MessageResponse(message="Logout realizado com sucesso.")
