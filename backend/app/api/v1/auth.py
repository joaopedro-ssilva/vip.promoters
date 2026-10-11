import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser
from app.core.config import settings
from app.core.errors import AppError, error_response
from app.core.rate_limit import check_rate_limit, client_ip
from app.core.security import (
    REFRESH_COOKIE,
    clear_session_cookies,
    create_access_token,
    dummy_verify,
    hash_password,
    hash_token,
    needs_rehash,
    new_refresh_token,
    set_session_cookies,
    verify_password,
)
from app.core.sessions import lock_families, lock_family, mark_revoked
from app.models import Membership, Organization, PromoterProfile, RefreshToken, User
from app.schemas.models import (
    ChangePasswordIn,
    LoginIn,
    PatchMeIn,
    RegisterIn,
    UserEnvelope,
)
from app.services.notifications import notify
from app.services.views import user_out

router = APIRouter(prefix="/auth", tags=["auth"])

INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sem 0 O 1 I L


def new_invite_code() -> str:
    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))


async def _issue_session(
    db, user: User, request: Request, response: Response, family_id: uuid.UUID | None = None
) -> None:
    raw, hashed = new_refresh_token()
    family_id = family_id or uuid.uuid4()
    db.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id,
            token_hash=hashed,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
            user_agent=(request.headers.get("user-agent") or "")[:255] or None,
        )
    )
    set_session_cookies(response, create_access_token(user.id, user.role, family_id), raw)


def _unauthenticated() -> JSONResponse:
    resp = error_response(401, "unauthenticated", "Sessão expirada. Faça login novamente.")
    clear_session_cookies(resp)
    return resp


@router.post("/register", status_code=201, response_model=UserEnvelope)
async def register(body: RegisterIn, request: Request, response: Response, db: DB):
    await check_rate_limit("register", f"ip:{client_ip(request)}")
    fields: dict[str, str] = {}
    if body.role == "manager" and not body.organization_name:
        fields["organization_name"] = "Informe o nome da sua equipe."
    if body.role == "promoter" and not body.instagram_username:
        fields["instagram_username"] = "Informe seu @ do Instagram."
    if fields:
        raise AppError(422, "validation_error", "Dados inválidos.", fields)

    if await db.scalar(select(User.id).where(User.email == body.email)):
        raise AppError(409, "email_taken", "Este e-mail já está cadastrado.")
    if body.role == "promoter":
        assert body.instagram_username is not None
        if await db.scalar(
            select(PromoterProfile.user_id).where(
                PromoterProfile.instagram_username == body.instagram_username
            )
        ):
            raise AppError(
                409, "instagram_username_taken", "Este @ do Instagram já está cadastrado."
            )
    invite_org: Organization | None = None
    if body.role == "promoter" and body.invite_code:
        invite_org = (
            await db.execute(
                select(Organization).where(
                    Organization.invite_code == body.invite_code.strip().upper()
                )
            )
        ).scalar_one_or_none()
        if invite_org is None:
            raise AppError(400, "invalid_invite", "Código de convite inválido.")

    password_hash = await hash_password(body.password)
    user = User(email=body.email, password_hash=password_hash, name=body.name, role=body.role)
    try:
        async with db.begin_nested():
            db.add(user)
            await db.flush()
    except IntegrityError:
        raise AppError(409, "email_taken", "Este e-mail já está cadastrado.") from None

    if body.role == "manager":
        for _ in range(5):
            org = Organization(
                owner_id=user.id, name=body.organization_name, invite_code=new_invite_code()
            )
            try:
                async with db.begin_nested():
                    db.add(org)
                    await db.flush()
                break
            except IntegrityError:
                continue
        else:  # pragma: no cover
            raise AppError(500, "internal_error", "Não foi possível criar a equipe.")
    else:
        try:
            async with db.begin_nested():
                db.add(PromoterProfile(user_id=user.id, instagram_username=body.instagram_username))
                await db.flush()
        except IntegrityError:
            raise AppError(
                409, "instagram_username_taken", "Este @ do Instagram já está cadastrado."
            ) from None
        if invite_org is not None:
            approved = invite_org.auto_approve_promoters
            db.add(
                Membership(
                    organization_id=invite_org.id,
                    promoter_id=user.id,
                    status="approved" if approved else "pending",
                    approved_at=datetime.now(UTC) if approved else None,
                )
            )
            await notify(
                db,
                invite_org.owner_id,
                "join_request",
                "Novo promoter na equipe" if approved else "Novo pedido para entrar na equipe",
                f"{user.name} (@{body.instagram_username}) "
                + ("entrou na equipe." if approved else "quer entrar na sua equipe."),
                "/gestor/equipe",
            )
    await _issue_session(db, user, request, response)
    await db.commit()
    return UserEnvelope(user=await user_out(db, user))


@router.post("/login", response_model=UserEnvelope)
async def login(body: LoginIn, request: Request, response: Response, db: DB):
    await check_rate_limit("login_ip", f"ip:{client_ip(request)}")
    await check_rate_limit(
        "login_account", "acct:" + hashlib.sha256(body.email.encode()).hexdigest()[:32]
    )
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if user is None:
        await dummy_verify(body.password)  # tempo constante para e-mail desconhecido
        valid = False
    else:
        valid = await verify_password(user.password_hash, body.password) and user.is_active
    if not valid or user is None:
        raise AppError(401, "invalid_credentials", "E-mail ou senha incorretos.")
    if needs_rehash(user.password_hash):
        user.password_hash = await hash_password(body.password)
    await _issue_session(db, user, request, response)
    await db.commit()
    return UserEnvelope(user=await user_out(db, user))


@router.post("/refresh", response_model=UserEnvelope)
async def refresh(request: Request, response: Response, db: DB):
    await check_rate_limit("refresh", f"ip:{client_ip(request)}")
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        return _unauthenticated()
    token_hash = hash_token(raw)
    family_id = await db.scalar(
        select(RefreshToken.family_id).where(RefreshToken.token_hash == token_hash)
    )
    if family_id is None:
        return _unauthenticated()
    # Serializa com logout/revogacao da mesma familia: um sucessor nunca nasce numa familia
    # que esta sendo revogada.
    await lock_family(db, family_id)
    rt = (
        await db.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if rt is None:
        return _unauthenticated()
    now = datetime.now(UTC)
    if rt.revoked_at is not None:
        # token ja rotacionado sendo reutilizado: revoga a familia inteira (e o acesso atual)
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == rt.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
        await mark_revoked([rt.family_id])
        return _unauthenticated()
    user = await db.get(User, rt.user_id)
    if rt.expires_at <= now or user is None or not user.is_active:
        rt.revoked_at = now
        await db.commit()
        await mark_revoked([rt.family_id])
        return _unauthenticated()
    rt.revoked_at = now
    await _issue_session(db, user, request, response, family_id=rt.family_id)
    await db.commit()
    return UserEnvelope(user=await user_out(db, user))


@router.post("/logout", status_code=204)
async def logout(request: Request, user: CurrentUser, db: DB):
    families: set[uuid.UUID] = {request.state.sid}
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        cookie_family = await db.scalar(
            select(RefreshToken.family_id).where(
                RefreshToken.token_hash == hash_token(raw), RefreshToken.user_id == user.id
            )
        )
        if cookie_family is not None:
            families.add(cookie_family)
    await lock_families(db, families)
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.family_id.in_(families),
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
    await mark_revoked(families)
    resp = Response(status_code=204)
    clear_session_cookies(resp)
    return resp


@router.get("/me", response_model=UserEnvelope)
async def me(user: CurrentUser, db: DB):
    return UserEnvelope(user=await user_out(db, user))


@router.patch("/me", response_model=UserEnvelope)
async def patch_me(body: PatchMeIn, user: CurrentUser, db: DB):
    user.name = body.name
    await db.commit()
    return UserEnvelope(user=await user_out(db, user))


@router.post("/change-password", status_code=204)
async def change_password(body: ChangePasswordIn, request: Request, user: CurrentUser, db: DB):
    await check_rate_limit("login_account", f"pwd:{user.id}")
    if not await verify_password(user.password_hash, body.current_password):
        raise AppError(
            422,
            "validation_error",
            "Dados inválidos.",
            {"current_password": "Senha atual incorreta."},
        )
    if body.current_password == body.new_password:
        raise AppError(
            422,
            "validation_error",
            "Dados inválidos.",
            {"new_password": "A nova senha deve ser diferente da atual."},
        )
    user.password_hash = await hash_password(body.new_password)
    current_family: uuid.UUID = request.state.sid  # familia da sessao que esta trocando a senha
    live = await db.execute(
        select(RefreshToken.family_id)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.family_id != current_family,
        )
        .distinct()
    )
    others = set(live.scalars())
    await lock_families(db, others)
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.family_id != current_family,
        )
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
    await mark_revoked(others)
    return Response(status_code=204)
