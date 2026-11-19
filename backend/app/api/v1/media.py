"""
CivicLens — Media Upload Endpoints
"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, Response
from app.dependencies import get_current_user
from app.exceptions import AccountNotVerifiedError, ForbiddenError, NotFoundError
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services.storage_service import UPLOAD_DIR, storage_service, verify_media_signature

router = APIRouter(prefix="/media", tags=["Media"])


@router.get("/files/{filename}", include_in_schema=False)
async def get_signed_media(
    filename: str,
    expires: int = Query(...),
    signature: str = Query(..., min_length=64, max_length=64),
) -> FileResponse:
    if not verify_media_signature(filename, expires, signature):
        raise ForbiddenError("Media link is invalid or expired")

    content = await storage_service.read_managed_file(filename)
    if content is None:
        path = UPLOAD_DIR / "complaints" / filename
        if path.is_file():
            return FileResponse(
                path,
                media_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
                headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
            )
        raise NotFoundError("Media file not found")
    return Response(
        content=content,
        media_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/upload", response_model=ApiResponse[dict[str, str | int]])
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[dict[str, str | int]]:
    if "citizen" in current_user.roles and not current_user.identity_verified:
        raise AccountNotVerifiedError()

    url = await storage_service.save_file(file, subfolder="complaints")
    file_name = file.filename or "media"
    return ApiResponse(
        success=True,
        data={
            "url": url,
            "filename": file_name,
            "file_size": file.size or 0,
            "mime_type": mimetypes.guess_type(file_name)[0] or "application/octet-stream",
        },
        message="File uploaded successfully",
    )
