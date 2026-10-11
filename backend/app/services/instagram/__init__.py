import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decrypt
from app.core.errors import AppError
from app.models import InstagramAccount
from app.models.base import AccountStatus
from app.services.instagram.base import (
    InstagramAuthError,
    InstagramClient,
    InstagramError,
)

log = logging.getLogger("app.instagram")
T = TypeVar("T")

_client: InstagramClient | None = None


def get_instagram_client() -> InstagramClient:
    global _client
    if _client is None:
        if settings.meta_mock_mode:
            from app.services.instagram.mock import MockInstagramClient

            _client = MockInstagramClient()
        else:
            from app.services.instagram.graph import GraphInstagramClient

            _client = GraphInstagramClient()
    return _client


async def close_instagram_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def call_with_account(
    db: AsyncSession,
    account: InstagramAccount,
    call: Callable[[InstagramClient, str], Awaitable[T]],
) -> T:
    """Executa uma chamada com o token da conta; mapeia erros para AppError.

    Token expirado/invalido marca a conta como `expired` (e confirma essa mudanca).
    """
    if account.status != AccountStatus.active.value:
        raise AppError(
            400,
            "instagram_not_connected",
            "A conexão com o Instagram expirou. Reconecte a conta.",
        )
    try:
        token = decrypt(account.access_token_enc)
    except ValueError:
        account.status = AccountStatus.expired.value
        await db.commit()
        raise AppError(
            400, "instagram_not_connected", "Reconecte sua conta do Instagram."
        ) from None
    try:
        return await call(get_instagram_client(), token)
    except InstagramAuthError:
        account.status = AccountStatus.expired.value
        await db.commit()
        raise AppError(
            502, "instagram_error", "A conexão com o Instagram expirou. Reconecte a conta."
        ) from None
    except InstagramError as exc:
        log.warning("instagram error", extra={"event": f"code={exc.code} status={exc.status}"})
        raise AppError(502, "instagram_error", f"Erro do Instagram: {exc}") from None
