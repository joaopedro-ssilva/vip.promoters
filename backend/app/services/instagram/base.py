"""Interface unica para a API do Instagram (login do Instagram) e tipos compartilhados."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


class InstagramError(Exception):
    """Erro tipado da API do Instagram."""

    def __init__(self, message: str, *, code: int | None = None, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.status = status


class InstagramAuthError(InstagramError):
    """Token expirado/invalido/revogado: a conta deve ser marcada como expired."""


class InstagramRateLimitError(InstagramError):
    pass


@dataclass
class TokenSet:
    access_token: str
    ig_user_id: str
    expires_at: datetime | None = None
    scopes: list[str] = field(default_factory=list)


@dataclass
class IGProfile:
    ig_user_id: str
    username: str
    name: str | None = None
    profile_picture_url: str | None = None
    account_type: str | None = None
    followers_count: int | None = None


@dataclass
class IGMedia:
    id: str
    caption: str | None = None
    media_type: str | None = None
    media_product_type: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    permalink: str | None = None
    timestamp: datetime | None = None
    like_count: int | None = None
    comments_count: int | None = None


@dataclass
class MediaPage:
    items: list[IGMedia]
    next_cursor: str | None = None


@dataclass
class IGComment:
    id: str
    text: str | None
    username: str | None
    from_id: str | None
    timestamp: datetime | None
    parent_id: str | None = None


@dataclass
class CommentPage:
    items: list[IGComment]
    next_cursor: str | None = None


class InstagramClient(ABC):
    @abstractmethod
    def authorize_url(self, state: str, redirect_uri: str, scopes: list[str], hint: str) -> str:
        """URL para onde o navegador e enviado para autorizar o app."""

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> TokenSet:
        """Troca o code por um token de longa duracao."""

    @abstractmethod
    async def refresh_token(self, access_token: str) -> TokenSet: ...

    @abstractmethod
    async def get_profile(self, access_token: str) -> IGProfile: ...

    @abstractmethod
    async def list_media(
        self, access_token: str, ig_user_id: str, after: str | None, limit: int
    ) -> MediaPage: ...

    @abstractmethod
    async def get_media(self, access_token: str, ig_user_id: str, media_id: str) -> IGMedia: ...

    @abstractmethod
    async def list_comments_page(
        self,
        access_token: str,
        ig_user_id: str,
        media_id: str,
        after: str | None,
        limit: int = 50,
    ) -> CommentPage:
        """Uma pagina de comentarios de primeiro nivel (mais recentes primeiro)."""

    @abstractmethod
    async def subscribe_webhooks(self, access_token: str, ig_user_id: str) -> bool: ...

    @abstractmethod
    async def create_media_container(
        self, access_token: str, ig_user_id: str, image_url: str, caption: str
    ) -> str:
        """Cria o container de midia (ainda nao publicado) e devolve o id."""

    @abstractmethod
    async def get_container_status(self, access_token: str, container_id: str) -> str:
        """IN_PROGRESS | FINISHED | PUBLISHED | ERROR | EXPIRED."""

    @abstractmethod
    async def publish_container(self, access_token: str, ig_user_id: str, container_id: str) -> str:
        """Publica um container ja criado e devolve o id da midia."""

    @abstractmethod
    async def find_published_media(
        self, access_token: str, ig_user_id: str, caption: str, since: datetime
    ) -> str | None:
        """Midia mais recente cuja legenda bate e cujo timestamp e >= since."""

    @abstractmethod
    async def get_user_username(self, access_token: str, scoped_id: str) -> str | None:
        """Resolve o @username de um IGSID (User Profile API)."""

    async def aclose(self) -> None:  # pragma: no cover - opcional
        return None
