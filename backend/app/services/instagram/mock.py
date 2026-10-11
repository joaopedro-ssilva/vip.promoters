"""Cliente Instagram simulado (META_MOCK_MODE=true).

O estado (posts publicados e comentarios simulados) fica no Redis para ser compartilhado
entre o backend e o worker; assim o polling (sync) enxerga os comentarios simulados.
"""

import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from app.core.config import settings
from app.core.redis import get_redis
from app.services.instagram.base import (
    CommentPage,
    IGComment,
    IGMedia,
    IGProfile,
    InstagramAuthError,
    InstagramClient,
    InstagramError,
    MediaPage,
    TokenSet,
)

MOCK_SCOPED_PREFIX = "mock_"
_BASE_MEDIA_ID = 17895000000000100
_CAPTIONS = [
    "Sexta VIP com line-up especial. Comenta aqui para entrar na lista!",
    "Aftermovie da última edição. Marca a galera!",
    "Novo drink da casa. Quem já provou?",
    "Sábado de open bar até meia-noite.",
    "Bastidores da produção. Vem com a gente!",
    "Pré-venda do próximo lote aberta.",
    "Playlist da noite por quem manda no som.",
    "Aniversariantes do mês entram free.",
]


def mock_ig_user_id(hint: str) -> str:
    """ID de usuario IG deterministico a partir do @username."""
    # hash do @ inteiro: usar so o prefixo fazia "orgteste1" e "orgteste2" colidirem
    digits = int.from_bytes(hashlib.sha256(hint.encode()).digest()[:8], "big") % 10**10
    return f"17841{digits:010d}"


def _base_media(ig_user_id: str) -> list[IGMedia]:
    now = datetime.now(UTC)
    items = []
    for i, caption in enumerate(_CAPTIONS):
        media_id = str(_BASE_MEDIA_ID + i)
        items.append(
            IGMedia(
                id=media_id,
                caption=caption,
                media_type="CAROUSEL_ALBUM" if i % 4 == 3 else "IMAGE",
                media_product_type="FEED",
                media_url=f"https://picsum.photos/seed/{media_id}/800/800",
                thumbnail_url=None,
                permalink=f"https://www.instagram.com/p/MOCK{media_id[-6:]}/",
                timestamp=now - timedelta(days=3 * (i + 1)),
                like_count=40 + i * 17,
                comments_count=3 + i,
            )
        )
    return items


def _media_to_json(m: IGMedia) -> str:
    d = m.__dict__.copy()
    d["timestamp"] = m.timestamp.isoformat() if m.timestamp else None
    return json.dumps(d)


def _media_from_json(raw: str) -> IGMedia:
    d = json.loads(raw)
    if d.get("timestamp"):
        d["timestamp"] = datetime.fromisoformat(d["timestamp"])
    return IGMedia(**d)


class MockInstagramClient(InstagramClient):
    # ------------------------------------------------------------------ OAuth
    def authorize_url(self, state: str, redirect_uri: str, scopes: list[str], hint: str) -> str:
        qs = urlencode({"state": state, "redirect_uri": redirect_uri, "hint": hint})
        return f"{settings.app_base_url}/api/v1/dev/instagram/authorize?{qs}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenSet:
        if not code.startswith("mock-"):
            raise InstagramError("Código de autorização inválido.", code=100, status=400)
        try:
            hint = base64.urlsafe_b64decode(code[5:] + "=" * (-len(code[5:]) % 4)).decode()
        except ValueError as exc:
            raise InstagramError("Código de autorização inválido.", code=100) from exc
        return TokenSet(
            access_token=f"mock_token_{hint}_{secrets.token_hex(6)}",
            ig_user_id=mock_ig_user_id(hint),
            expires_at=datetime.now(UTC) + timedelta(days=60),
            scopes=["instagram_business_basic", "instagram_business_manage_comments"],
        )

    async def refresh_token(self, access_token: str) -> TokenSet:
        self._check(access_token)
        hint = access_token.removeprefix("mock_token_").rsplit("_", 1)[0]
        return TokenSet(
            access_token=access_token,
            ig_user_id=mock_ig_user_id(hint),
            expires_at=datetime.now(UTC) + timedelta(days=60),
        )

    @staticmethod
    def _check(access_token: str) -> None:
        if not access_token.startswith("mock_token_"):
            raise InstagramAuthError("Token inválido.", code=190, status=401)

    @staticmethod
    def _hint(access_token: str) -> str:
        return access_token.removeprefix("mock_token_").rsplit("_", 1)[0]

    async def get_profile(self, access_token: str) -> IGProfile:
        self._check(access_token)
        hint = self._hint(access_token)
        return IGProfile(
            ig_user_id=mock_ig_user_id(hint),
            username=hint,
            name=hint.replace(".", " ").replace("_", " ").title(),
            profile_picture_url=f"https://picsum.photos/seed/{hint}/200/200",
            account_type="BUSINESS",
            followers_count=1200 + len(hint) * 37,
        )

    # ------------------------------------------------------------------ midia
    async def _all_media(self, ig_user_id: str) -> list[IGMedia]:
        r = get_redis()
        published = await r.lrange(f"mock:published:{ig_user_id}", 0, -1)
        items = [_media_from_json(p) for p in published]
        return items + _base_media(ig_user_id)

    async def list_media(
        self, access_token: str, ig_user_id: str, after: str | None, limit: int
    ) -> MediaPage:
        self._check(access_token)
        items = await self._all_media(ig_user_id)
        start = int(after) if after and after.isdigit() else 0
        page = items[start : start + limit]
        nxt = str(start + limit) if start + limit < len(items) else None
        return MediaPage(items=page, next_cursor=nxt)

    async def get_media(self, access_token: str, ig_user_id: str, media_id: str) -> IGMedia:
        self._check(access_token)
        for m in await self._all_media(ig_user_id):
            if m.id == media_id:
                return m
        raise InstagramError("Mídia não encontrada.", code=100, status=400)

    async def create_media_container(
        self, access_token: str, ig_user_id: str, image_url: str, caption: str
    ) -> str:
        self._check(access_token)
        container_id = f"179{secrets.randbelow(10**14):014d}"
        await get_redis().set(
            f"mock:container:{container_id}",
            json.dumps(
                {
                    "status": "FINISHED",
                    "image_url": image_url,
                    "caption": caption,
                    "created": datetime.now(UTC).isoformat(),
                    "media_id": None,
                }
            ),
            ex=86400,
        )
        return container_id

    async def _container(self, container_id: str) -> dict:
        raw = await get_redis().get(f"mock:container:{container_id}")
        if raw is None:
            raise InstagramError("Container não encontrado.", code=100, status=400)
        return json.loads(raw)

    async def get_container_status(self, access_token: str, container_id: str) -> str:
        self._check(access_token)
        return (await self._container(container_id))["status"]

    async def publish_container(self, access_token: str, ig_user_id: str, container_id: str) -> str:
        self._check(access_token)
        c = await self._container(container_id)
        if c["status"] == "PUBLISHED":
            raise InstagramError("O container já foi publicado.", code=9007, status=400)
        media_id = f"179{secrets.randbelow(10**14):014d}"
        media = IGMedia(
            id=media_id,
            caption=c["caption"],
            media_type="IMAGE",
            media_product_type="FEED",
            media_url=c["image_url"],
            permalink=f"https://www.instagram.com/p/MOCK{media_id[-6:]}/",
            timestamp=datetime.now(UTC),
            like_count=0,
            comments_count=0,
        )
        r = get_redis()
        await r.lpush(f"mock:published:{ig_user_id}", _media_to_json(media))
        c.update(status="PUBLISHED", media_id=media_id)
        await r.set(f"mock:container:{container_id}", json.dumps(c), ex=86400)
        return media_id

    async def find_published_media(
        self, access_token: str, ig_user_id: str, caption: str, since: datetime
    ) -> str | None:
        self._check(access_token)
        best: IGMedia | None = None
        for m in await self._all_media(ig_user_id):
            if (m.caption or "").strip() != caption.strip():
                continue
            if m.timestamp is None or m.timestamp < since:
                continue
            if best is None or m.timestamp > (best.timestamp or since):
                best = m
        return best.id if best else None

    # ------------------------------------------------------------ comentarios
    async def list_comments_page(
        self,
        access_token: str,
        ig_user_id: str,
        media_id: str,
        after: str | None,
        limit: int = 50,
    ) -> CommentPage:
        self._check(access_token)
        raw = await get_redis().lrange(f"mock:comments:{ig_user_id}:{media_id}", 0, -1)
        raw.reverse()  # mais recentes primeiro, como na API real
        start = int(after) if after and after.isdigit() else 0
        out = []
        for item in raw[start : start + limit]:
            d = json.loads(item)
            out.append(
                IGComment(
                    id=d["id"],
                    text=d.get("text"),
                    username=d.get("username"),
                    from_id=d.get("from_id"),
                    timestamp=datetime.fromisoformat(d["timestamp"]),
                )
            )
        nxt = str(start + limit) if start + limit < len(raw) else None
        return CommentPage(items=out, next_cursor=nxt)

    async def subscribe_webhooks(self, access_token: str, ig_user_id: str) -> bool:
        self._check(access_token)
        return True

    async def get_user_username(self, access_token: str, scoped_id: str) -> str | None:
        self._check(access_token)
        if scoped_id.startswith(MOCK_SCOPED_PREFIX):
            return scoped_id.removeprefix(MOCK_SCOPED_PREFIX)
        return None


async def mock_store_comment(
    ig_user_id: str,
    media_id: str,
    comment_id: str,
    username: str,
    from_id: str,
    text: str,
    timestamp: datetime,
) -> None:
    """Guarda um comentario simulado para que o polling tambem o enxergue."""
    payload = json.dumps(
        {
            "id": comment_id,
            "username": username,
            "from_id": from_id,
            "text": text,
            "timestamp": timestamp.isoformat(),
        }
    )
    r = get_redis()
    key = f"mock:comments:{ig_user_id}:{media_id}"
    await r.rpush(key, payload)
    await r.expire(key, 7 * 86400)
