"""Cliente real: "Instagram API with Instagram Login" (graph.instagram.com)."""

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.services.instagram.base import (
    CommentPage,
    IGComment,
    IGMedia,
    IGProfile,
    InstagramAuthError,
    InstagramClient,
    InstagramError,
    InstagramRateLimitError,
    MediaPage,
    TokenSet,
)

log = logging.getLogger("app.instagram")

AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
GRAPH_HOST = "https://graph.instagram.com"
MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,media_url,thumbnail_url,permalink,"
    "timestamp,like_count,comments_count"
)
RATE_LIMIT_CODES = {4, 17, 32, 613}
AUTH_CODES = {102, 190}
MAX_ATTEMPTS = 3


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # A API devolve "2026-10-01T12:00:00+0000"
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").astimezone(UTC)
    except ValueError:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            return None


def _to_media(d: dict[str, Any]) -> IGMedia:
    return IGMedia(
        id=str(d["id"]),
        caption=d.get("caption"),
        media_type=d.get("media_type"),
        media_product_type=d.get("media_product_type"),
        media_url=d.get("media_url"),
        thumbnail_url=d.get("thumbnail_url"),
        permalink=d.get("permalink"),
        timestamp=_parse_ts(d.get("timestamp")),
        like_count=d.get("like_count"),
        comments_count=d.get("comments_count"),
    )


class GraphInstagramClient(InstagramClient):
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            headers={"User-Agent": "vip-promoters/1.0"},
        )
        self._base = f"{GRAPH_HOST}/{settings.meta_graph_version}"

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------- transporte
    @staticmethod
    def _raise_for_error(resp: httpx.Response) -> None:
        try:
            body = resp.json()
        except ValueError:
            body = {}
        err = body.get("error") if isinstance(body, dict) else None
        message = "Erro na API do Instagram."
        code = None
        if isinstance(err, dict):
            message = str(err.get("message") or message)[:300]
            code = err.get("code")
        elif isinstance(body, dict) and body.get("error_message"):
            message = str(body["error_message"])[:300]
            code = body.get("code")
        if (
            resp.status_code == 401
            or code in AUTH_CODES
            or (isinstance(err, dict) and err.get("type") == "OAuthException" and code == 190)
        ):
            raise InstagramAuthError(message, code=code, status=resp.status_code)
        if resp.status_code == 429 or code in RATE_LIMIT_CODES:
            raise InstagramRateLimitError(message, code=code, status=resp.status_code)
        raise InstagramError(message, code=code, status=resp.status_code)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        retry: bool = True,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        last: Exception | None = None
        attempts = MAX_ATTEMPTS if retry else 1
        for attempt in range(attempts):
            try:
                resp = await self._http.request(
                    method, url, params=params, data=data, headers=headers
                )
            except httpx.TransportError as exc:
                last = InstagramError("Falha de rede ao falar com o Instagram.")
                log.warning("instagram transport error", extra={"event": type(exc).__name__})
            else:
                if resp.status_code < 400:
                    try:
                        payload = resp.json()
                    except ValueError as exc:
                        raise InstagramError("Resposta inválida do Instagram.") from exc
                    return payload if isinstance(payload, dict) else {"data": payload}
                retryable = resp.status_code == 429 or resp.status_code >= 500
                try:
                    self._raise_for_error(resp)
                except InstagramRateLimitError as exc:
                    last = exc
                    retryable = True
                except InstagramError as exc:
                    if not retryable:
                        raise
                    last = exc
                if not retryable:
                    raise last  # pragma: no cover
            if attempt < attempts - 1:
                await asyncio.sleep(0.5 * (2**attempt) + random.random() * 0.25)
        assert last is not None
        raise last

    # ------------------------------------------------------------------ OAuth
    def authorize_url(self, state: str, redirect_uri: str, scopes: list[str], hint: str) -> str:
        qs = urlencode(
            {
                "client_id": settings.meta_app_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": ",".join(scopes),
                "state": state,
            }
        )
        return f"{AUTHORIZE_URL}?{qs}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenSet:
        short = await self._request(
            "POST",
            TOKEN_URL,
            data={
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        if isinstance(short.get("data"), list) and short["data"]:
            short = short["data"][0]
        short_token = short.get("access_token")
        if not short_token:
            raise InstagramError("O Instagram não devolveu um token.")
        long = await self._request(
            "GET",
            f"{GRAPH_HOST}/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": settings.meta_app_secret,
                "access_token": short_token,
            },
        )
        perms = short.get("permissions")
        scopes = perms.split(",") if isinstance(perms, str) else list(perms) if perms else []
        return TokenSet(
            access_token=long.get("access_token", short_token),
            ig_user_id=str(short.get("user_id", "")),
            expires_at=datetime.now(UTC) + timedelta(seconds=int(long.get("expires_in", 5184000))),
            scopes=scopes,
        )

    async def refresh_token(self, access_token: str) -> TokenSet:
        data = await self._request(
            "GET",
            f"{GRAPH_HOST}/refresh_access_token",
            params={"grant_type": "ig_refresh_token", "access_token": access_token},
        )
        return TokenSet(
            access_token=data.get("access_token", access_token),
            ig_user_id="",
            expires_at=datetime.now(UTC) + timedelta(seconds=int(data.get("expires_in", 5184000))),
        )

    async def get_profile(self, access_token: str) -> IGProfile:
        d = await self._request(
            "GET",
            f"{self._base}/me",
            token=access_token,
            params={
                "fields": "user_id,username,name,account_type,profile_picture_url,followers_count"
            },
        )
        ig_id = d.get("user_id") or d.get("id")
        if not ig_id or not d.get("username"):
            raise InstagramError("Perfil do Instagram incompleto.")
        return IGProfile(
            ig_user_id=str(ig_id),
            username=str(d["username"]),
            name=d.get("name"),
            profile_picture_url=d.get("profile_picture_url"),
            account_type=d.get("account_type"),
            followers_count=d.get("followers_count"),
        )

    # ------------------------------------------------------------------ midia
    async def list_media(
        self, access_token: str, ig_user_id: str, after: str | None, limit: int
    ) -> MediaPage:
        params: dict[str, Any] = {"fields": MEDIA_FIELDS, "limit": limit}
        if after:
            params["after"] = after
        d = await self._request(
            "GET", f"{self._base}/{ig_user_id}/media", token=access_token, params=params
        )
        paging = d.get("paging") or {}
        nxt = (paging.get("cursors") or {}).get("after") if paging.get("next") else None
        return MediaPage(items=[_to_media(m) for m in d.get("data", [])], next_cursor=nxt)

    async def get_media(self, access_token: str, ig_user_id: str, media_id: str) -> IGMedia:
        d = await self._request(
            "GET", f"{self._base}/{media_id}", token=access_token, params={"fields": MEDIA_FIELDS}
        )
        return _to_media(d)

    async def list_comments_page(
        self,
        access_token: str,
        ig_user_id: str,
        media_id: str,
        after: str | None,
        limit: int = 50,
    ) -> CommentPage:
        params: dict[str, Any] = {
            "fields": "id,text,timestamp,username,from,parent_id",
            "limit": limit,
        }
        if after:
            params["after"] = after
        d = await self._request(
            "GET", f"{self._base}/{media_id}/comments", token=access_token, params=params
        )
        items: list[IGComment] = []
        for c in d.get("data", []):
            frm = c.get("from") or {}
            items.append(
                IGComment(
                    id=str(c["id"]),
                    text=c.get("text"),
                    username=c.get("username") or frm.get("username"),
                    from_id=str(frm["id"]) if frm.get("id") else None,
                    timestamp=_parse_ts(c.get("timestamp")),
                    parent_id=str(c["parent_id"]) if c.get("parent_id") else None,
                )
            )
        paging = d.get("paging") or {}
        nxt = (paging.get("cursors") or {}).get("after") if paging.get("next") else None
        return CommentPage(items=items, next_cursor=nxt)

    async def subscribe_webhooks(self, access_token: str, ig_user_id: str) -> bool:
        d = await self._request(
            "POST",
            f"{self._base}/{ig_user_id}/subscribed_apps",
            token=access_token,
            params={"subscribed_fields": "comments,messages"},
        )
        return bool(d.get("success"))

    async def create_media_container(
        self, access_token: str, ig_user_id: str, image_url: str, caption: str
    ) -> str:
        container = await self._request(
            "POST",
            f"{self._base}/{ig_user_id}/media",
            token=access_token,
            data={"image_url": image_url, "caption": caption},
            retry=False,  # nao idempotente: nunca criar dois containers
        )
        container_id = container.get("id")
        if not container_id:
            raise InstagramError("O Instagram não criou o container de mídia.")
        return str(container_id)

    async def get_container_status(self, access_token: str, container_id: str) -> str:
        d = await self._request(
            "GET",
            f"{self._base}/{container_id}",
            token=access_token,
            params={"fields": "status_code"},
        )
        return str(d.get("status_code") or "IN_PROGRESS")

    async def publish_container(self, access_token: str, ig_user_id: str, container_id: str) -> str:
        published = await self._request(
            "POST",
            f"{self._base}/{ig_user_id}/media_publish",
            token=access_token,
            data={"creation_id": container_id},
            retry=False,  # nao idempotente: o chamador reconcilia pelo status do container
        )
        media_id = published.get("id")
        if not media_id:
            raise InstagramError("Falha ao publicar no Instagram.")
        return str(media_id)

    async def find_published_media(
        self, access_token: str, ig_user_id: str, caption: str, since: datetime
    ) -> str | None:
        page = await self.list_media(access_token, ig_user_id, None, 25)
        best: IGMedia | None = None
        for m in page.items:
            if (m.caption or "").strip() != caption.strip():
                continue
            if m.timestamp is None or m.timestamp < since:
                continue
            if best is None or m.timestamp > (best.timestamp or since):
                best = m
        return best.id if best else None

    async def get_user_username(self, access_token: str, scoped_id: str) -> str | None:
        d = await self._request(
            "GET", f"{self._base}/{scoped_id}", token=access_token, params={"fields": "username"}
        )
        return d.get("username")
