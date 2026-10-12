import re
from datetime import UTC, datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, Manager
from app.core.config import settings
from app.core.crypto import encrypt
from app.core.errors import AppError
from app.core.security import (
    ACCESS_COOKIE,
    OAUTH_COOKIE_PATH,
    OAUTH_STATE_COOKIE,
    decode_access_token,
    sign_state,
    verify_state,
)
from app.core.sessions import is_revoked
from app.models import InstagramAccount, Organization, PromoterProfile, User
from app.models.base import AccountStatus
from app.schemas.models import (
    AuthorizeUrlOut,
    InstagramAccountEnvelope,
    InstagramAccountOut,
    MediaListOut,
)
from app.services.campaigns import get_account, list_media_cached, require_account
from app.services.instagram import get_instagram_client
from app.services.instagram.base import InstagramAuthError, InstagramError

router = APIRouter(prefix="/instagram", tags=["instagram"])

MANAGER_SCOPES = [
    "instagram_business_basic",
    "instagram_business_manage_comments",
    "instagram_business_manage_messages",
    "instagram_business_content_publish",
]


def _account_out(a: InstagramAccount) -> InstagramAccountOut:
    return InstagramAccountOut(
        ig_user_id=a.ig_user_id,
        username=a.username,
        name=a.name,
        profile_picture_url=a.profile_picture_url,
        account_type=a.account_type,
        followers_count=a.followers_count,
        status=a.status,
        token_expires_at=a.token_expires_at,
        webhook_subscribed=a.webhook_subscribed,
        connected_at=a.connected_at,
        scopes=list(a.scopes or []),
    )


@router.get("/account", response_model=InstagramAccountEnvelope)
async def get_my_account(user: CurrentUser, db: DB):
    if user.role != "manager":
        return InstagramAccountEnvelope(account=None)
    account = await get_account(db, user.id)
    return InstagramAccountEnvelope(account=_account_out(account) if account else None)


@router.post("/connect", response_model=AuthorizeUrlOut)
async def connect(user: CurrentUser, db: DB, response: Response):
    if user.role == "manager":
        org = (
            await db.execute(select(Organization).where(Organization.owner_id == user.id))
        ).scalar_one()
        hint = re.sub(r"[^a-z0-9._]", "", org.name.lower().replace(" ", "")) or "conta.demo"
        scopes = MANAGER_SCOPES
    else:
        # A verificacao do promoter e por codigo em comentario (POST
        # /promoter/verification): o login do Instagram so aceita conta profissional e pedir
        # permissao a promoter aumentaria o escopo do App Review sem necessidade.
        raise AppError(
            400,
            "use_comment_verification",
            "Para verificar seu @, use o código de verificação no seu perfil.",
        )
    state = sign_state(user.id)
    url = get_instagram_client().authorize_url(state, settings.redirect_uri, scopes, hint[:30])
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=600,
        path=OAUTH_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return AuthorizeUrlOut(authorize_url=url)


def _redirect(role: str | None, status: str, reason: str | None = None) -> RedirectResponse:
    base = "/promoter/perfil" if role == "promoter" else "/gestor/instagram"
    qs = {"status": status}
    if reason:
        qs["reason"] = reason
    resp = RedirectResponse(f"{settings.app_base_url}{base}?{urlencode(qs)}", status_code=302)
    resp.delete_cookie(
        OAUTH_STATE_COOKIE,
        path=OAUTH_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return resp


@router.get("/callback", include_in_schema=True)
async def callback(
    request: Request,
    db: DB,
    code: str | None = Query(None, max_length=2048),
    state: str | None = Query(None, max_length=512),
    error: str | None = Query(None, max_length=200),
):
    token = request.cookies.get(ACCESS_COOKIE)
    decoded = decode_access_token(token) if token else None
    if decoded and await is_revoked(db, decoded[1]):
        decoded = None
    user = await db.get(User, decoded[0]) if decoded else None
    if user is None or not user.is_active:
        return RedirectResponse(f"{settings.app_base_url}/entrar", status_code=302)
    role = user.role
    if error:
        return _redirect(role, "error", "denied")
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not code or not state or cookie_state != state or verify_state(state) != user.id:
        return _redirect(role, "error", "invalid_state")

    client = get_instagram_client()
    try:
        tokens = await client.exchange_code(code, settings.redirect_uri)
        profile = await client.get_profile(tokens.access_token)
    except InstagramAuthError:
        return _redirect(role, "error", "exchange_failed")
    except InstagramError:
        return _redirect(role, "error", "instagram_error")

    if role == "promoter":
        own = await db.get(PromoterProfile, user.id)
        if own is None or profile.username.lower() != own.instagram_username:
            return _redirect(role, "error", "username_mismatch")
        own.verified = True
        own.verified_at = datetime.now(UTC)
        own.verification_method = "oauth"
        own.ig_scoped_id = profile.ig_user_id
        await db.commit()
        return _redirect(role, "connected")

    other = await db.scalar(
        select(InstagramAccount.user_id).where(
            InstagramAccount.ig_user_id == profile.ig_user_id,
            InstagramAccount.user_id != user.id,
        )
    )
    if other is not None:
        return _redirect(role, "error", "already_connected")
    subscribed = False
    try:
        subscribed = await client.subscribe_webhooks(tokens.access_token, profile.ig_user_id)
    except InstagramError:
        subscribed = False
    account = await get_account(db, user.id)
    if account is None:
        account = InstagramAccount(user_id=user.id, ig_user_id=profile.ig_user_id, username="")
        account.access_token_enc = ""
        db.add(account)
    account.ig_user_id = profile.ig_user_id
    account.username = profile.username
    account.name = profile.name
    account.profile_picture_url = profile.profile_picture_url
    account.account_type = profile.account_type
    account.followers_count = profile.followers_count
    account.access_token_enc = encrypt(tokens.access_token)
    account.token_expires_at = tokens.expires_at
    account.scopes = tokens.scopes or MANAGER_SCOPES
    account.webhook_subscribed = subscribed
    account.status = AccountStatus.active.value
    account.connected_at = datetime.now(UTC)
    await db.commit()
    return _redirect(role, "connected")


@router.delete("/account", status_code=204)
async def disconnect(user: CurrentUser, db: DB):
    if user.role == "manager":
        account = await get_account(db, user.id)
        if account is not None:
            await db.delete(account)
    else:
        profile = await db.get(PromoterProfile, user.id)
        if profile is not None:
            profile.verified = False
            profile.verified_at = None
            profile.verification_method = None
    await db.commit()
    return Response(status_code=204)


@router.get("/media", response_model=MediaListOut)
async def list_media(
    ctx: Manager,
    db: DB,
    after: str | None = Query(None, max_length=512),
    limit: int = Query(12, ge=1, le=50),
):
    account = await require_account(db, ctx.org)
    return MediaListOut(**await list_media_cached(db, account, after, limit))
