import re
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, BeforeValidator, StringConstraints

from app.core.config import settings

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_USERNAME_RE = re.compile(r"^[a-z0-9._]{1,30}$")


def _email(v: str) -> str:
    v = v.strip().lower()
    if len(v) > 254 or not _EMAIL_RE.match(v):
        raise ValueError("E-mail inválido.")
    return v


def _password(v: str) -> str:
    if len(v) < 8 or not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("A senha deve ter ao menos 8 caracteres, com letras e números.")
    return v


def _norm_username(v: object) -> object:
    if isinstance(v, str):
        return v.strip().lstrip("@").lower()
    return v


def _check_username(v: str) -> str:
    if not _USERNAME_RE.match(v):
        raise ValueError("Usuário do Instagram inválido (letras, números, . e _; até 30).")
    return v


def _image_url(v: str) -> str:
    if len(v) > 2000:
        raise ValueError("URL longa demais.")
    if v.startswith("https://") or v.startswith(settings.app_base_url + "/"):
        return v
    raise ValueError("Use uma URL de imagem https:// válida.")


Email = Annotated[str, AfterValidator(_email)]
Password = Annotated[str, StringConstraints(max_length=128), AfterValidator(_password)]
LoginPassword = Annotated[str, StringConstraints(min_length=1, max_length=128)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
IGUsername = Annotated[str, BeforeValidator(_norm_username), AfterValidator(_check_username)]
ImageUrl = Annotated[str, AfterValidator(_image_url)]
InviteCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16)]
