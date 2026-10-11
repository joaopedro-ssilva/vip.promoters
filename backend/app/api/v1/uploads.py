from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import Manager
from app.core.config import settings
from app.core.errors import AppError, not_found
from app.core.rate_limit import check_rate_limit
from app.schemas.models import UploadOut
from app.services.uploads import resolve_path, save_image

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/image", status_code=201, response_model=UploadOut)
async def upload_image(request: Request, ctx: Manager, file: UploadFile = File(...)):
    await check_rate_limit("upload", f"user:{ctx.user.id}")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > settings.upload_max_bytes + 64 * 1024:
        raise AppError(400, "upload_invalid", "A imagem deve ter no máximo 8 MB.")
    data = await file.read(settings.upload_max_bytes + 1)
    if len(data) > settings.upload_max_bytes:
        raise AppError(400, "upload_invalid", "A imagem deve ter no máximo 8 MB.")
    return UploadOut(url=await save_image(data))


@router.get("/{filename}")
async def get_upload(filename: str):
    path = resolve_path(filename)
    if path is None:
        raise not_found()
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )
