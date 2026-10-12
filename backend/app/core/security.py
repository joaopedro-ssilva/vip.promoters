"""Senhas (Argon2id), JWT de acesso, tokens opacos de refresh, state OAuth e cookies."""

import asyncio
import hashlib
import hmac
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE = "vip_access"
REFRESH_COOKIE = "vip_refresh"
SESSION_COOKIE = "vip_session"
OAUTH_STATE_COOKIE = "vip_oauth_state"
REFRESH_COOKIE_PATH = "/api/v1/auth"
OAUTH_COOKIE_PATH = "/api/v1/instagram"

_ph = PasswordHasher()  # Argon2id com os parametros padrao recomendados
_DUMMY_HASH = _ph.hash("dummy-password-for-constant-time")


def _verify_sync(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_ph.hash, password)


async def verify_password(password_hash: str, password: str) -> bool:
    return await asyncio.to_thread(_verify_sync, password_hash, password)


async def dummy_verify(password: str) -> None:
    """Gasta o mesmo tempo de uma verificacao real (e-mail desconhecido)."""
    await asyncio.to_thread(_verify_sync, _DUMMY_HASH, password)


def needs_rehash(password_hash: str) -> bool:
    return _ph.check_needs_rehash(password_hash)


# ---------------------------------------------------------------- JWT de acesso


def create_access_token(user_id: uuid.UUID, role: str, sid: uuid.UUID) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "role": role,
        "sid": str(sid),  # familia do refresh token: permite revogar o acesso na hora
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(claims, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> tuple[uuid.UUID, uuid.UUID] | None:
    """Devolve (user_id, sid) ou None. Tokens sem sid sao rejeitados.

    Aceita tokens assinados com SECRET_KEY ou com uma chave de SECRET_KEY_PREVIOUS (rotacao
    sem derrubar quem esta logado; o access token vive 15 minutos)."""
    for key in settings.secret_keys:
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=["HS256"],
                options={"require": ["exp", "sub", "typ", "sid"]},
            )
        except jwt.InvalidSignatureError:
            continue
        except (jwt.PyJWTError, ValueError):
            return None
        try:
            if claims.get("typ") != "access":
                return None
            return uuid.UUID(claims["sub"]), uuid.UUID(claims["sid"])
        except (KeyError, ValueError):
            return None
    return None


# ---------------------------------------------------------------- refresh opaco


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


# ---------------------------------------------------------------- state OAuth


def _state_sig(payload: str, key: str | None = None) -> str:
    return hmac.new(
        (key or settings.secret_key).encode(), f"oauth-state:{payload}".encode(), hashlib.sha256
    ).hexdigest()


def sign_state(user_id: uuid.UUID, ttl_seconds: int = 600) -> str:
    payload = f"{user_id}:{int(time.time()) + ttl_seconds}:{secrets.token_hex(8)}"
    return f"{payload}:{_state_sig(payload)}"


def verify_state(state: str) -> uuid.UUID | None:
    try:
        uid, exp, nonce, sig = state.split(":")
        payload = f"{uid}:{exp}:{nonce}"
        if not any(hmac.compare_digest(sig, _state_sig(payload, k)) for k in settings.secret_keys):
            return None
        if int(exp) < time.time():
            return None
        return uuid.UUID(uid)
    except ValueError:
        return None


# ---------------------------------------------------------------- cookies


def set_session_cookies(response: Response, access: str, refresh: str) -> None:
    refresh_seconds = settings.refresh_token_days * 86400
    secure = settings.cookie_secure
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        max_age=settings.access_token_minutes * 60,
        path="/",
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=refresh_seconds,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    response.set_cookie(
        SESSION_COOKIE,
        "1",
        max_age=refresh_seconds,
        path="/",
        httponly=False,
        samesite="lax",
        secure=secure,
    )


def clear_session_cookies(response: Response) -> None:
    secure = settings.cookie_secure
    response.delete_cookie(ACCESS_COOKIE, path="/", httponly=True, samesite="lax", secure=secure)
    response.delete_cookie(
        REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, httponly=True, samesite="lax", secure=secure
    )
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=False, samesite="lax", secure=secure)
