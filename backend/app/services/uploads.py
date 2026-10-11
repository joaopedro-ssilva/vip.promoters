"""Uploads de imagem: decodifica com Pillow, reencoda como JPEG e guarda com nome aleatorio."""

import asyncio
import io
import re
import secrets
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings
from app.core.errors import AppError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_SIDE = 8000
MAX_PIXELS = 40_000_000
OUTPUT_MAX_SIDE = 2048
FILENAME_RE = re.compile(r"^[a-f0-9]{32}\.jpg$")

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def _invalid(message: str = "Envie uma imagem válida (JPEG, PNG ou WebP).") -> AppError:
    return AppError(400, "upload_invalid", message)


def _reencode(data: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(data))
            if img.format not in ALLOWED_FORMATS:
                raise _invalid()
            width, height = img.size
            if (
                width < 1
                or height < 1
                or max(width, height) > MAX_SIDE
                or width * height > MAX_PIXELS
            ):
                raise _invalid("Imagem com dimensões grandes demais.")
            img.load()
            img = ImageOps.exif_transpose(img)
            if img.mode in ("RGBA", "LA", "P"):
                rgba = img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.getchannel("A"))
                img = background
            else:
                img = img.convert("RGB")
            img.thumbnail((OUTPUT_MAX_SIDE, OUTPUT_MAX_SIDE))
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=88, optimize=True)  # sem EXIF/metadados
            return out.getvalue()
    except AppError:
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
        SyntaxError,
        MemoryError,
    ):
        raise _invalid() from None


async def save_image(data: bytes) -> str:
    if not data:
        raise _invalid()
    jpeg = await asyncio.to_thread(_reencode, data)
    name = f"{secrets.token_hex(16)}.jpg"
    directory = Path(settings.upload_dir)

    def _write() -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_bytes(jpeg)

    await asyncio.to_thread(_write)
    return f"{settings.app_base_url}/api/v1/uploads/{name}"


def resolve_path(filename: str) -> Path | None:
    """Caminho seguro de um upload ou None (rejeita qualquer coisa fora do padrao)."""
    if not FILENAME_RE.match(filename):
        return None
    base = Path(settings.upload_dir).resolve()
    path = (base / filename).resolve()
    if path.parent != base or not path.is_file():
        return None
    return path
