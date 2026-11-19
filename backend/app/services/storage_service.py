"""
CivicLens — Storage Service
Handles media uploads with validation, file type checks, and path generation.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
import uuid
from functools import lru_cache
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode, urlparse

from fastapi import UploadFile

from app.config import Settings, get_settings
from app.exceptions import ValidationError
from app.services.storage_backends import (
    LocalStorageBackend,
    S3StorageBackend,
    StorageBackend,
)

UPLOAD_DIR = Path("uploads")
ALLOWED_SIGNATURES = {
    ".jpg": lambda content: content.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda content: content.startswith(b"\xff\xd8\xff"),
    ".png": lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
    ".webp": lambda content: len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
    ".mp4": lambda content: len(content) >= 12 and content[4:8] == b"ftyp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MEDIA_URL_TTL_SECONDS = 3600


def is_managed_media_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        return False
    parts = PurePosixPath(parsed.path).parts
    if len(parts) != 4 or parts[:3] != ("/", "uploads", "complaints"):
        return False
    return re.fullmatch(r"[0-9a-f]{32}\.(jpg|jpeg|png|webp|mp4)", parts[3]) is not None


def signed_media_url(file_url: str) -> str:
    settings = get_settings()
    if not is_managed_media_url(file_url):
        return file_url

    filename = PurePosixPath(file_url).name
    expires = int(time.time()) + MEDIA_URL_TTL_SECONDS
    message = f"{filename}:{expires}".encode()
    signature = hmac.new(
        settings.MEDIA_SIGNING_SECRET.encode(), message, hashlib.sha256
    ).hexdigest()
    path = f"/api/v1/media/files/{filename}"
    query = urlencode({"expires": expires, "signature": signature})
    return f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}{path}?{query}"


def verify_media_signature(filename: str, expires: int, signature: str) -> bool:
    if not is_managed_media_url(f"/uploads/complaints/{filename}"):
        return False
    settings = get_settings()
    now = int(time.time())
    if expires <= now or expires > now + MEDIA_URL_TTL_SECONDS:
        return False
    message = f"{filename}:{expires}".encode()
    expected = hmac.new(
        settings.MEDIA_SIGNING_SECRET.encode(), message, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@lru_cache
def get_storage_backend(settings: Settings | None = None) -> StorageBackend:
    cfg = settings or get_settings()
    if cfg.STORAGE_BACKEND == "s3":
        return S3StorageBackend(cfg)
    return LocalStorageBackend(UPLOAD_DIR)


class StorageService:
    def __init__(self, base_url: str = "/uploads", backend: StorageBackend | None = None):
        self.base_url = base_url
        self._backend = backend or get_storage_backend()
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file: UploadFile, subfolder: str = "complaints") -> str:
        if subfolder != "complaints":
            raise ValidationError("Unsupported upload destination")
        if not file.filename:
            raise ValidationError("File must have a valid filename")

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_SIGNATURES:
            raise ValidationError(f"File extension '{ext}' is not permitted")

        filename = f"{uuid.uuid4().hex}{ext}"
        content, signature = await self._read_validated_upload(file, ext)
        key = f"{subfolder}/{filename}"
        await self._backend.put_object(key, content)
        return f"{self.base_url}/{subfolder}/{filename}"

    async def read_managed_file(self, filename: str) -> bytes | None:
        key = f"complaints/{filename}"
        return await self._backend.get_object(key)

    async def read_file_url(self, file_url: str) -> bytes | None:
        """Read only a CivicLens-managed object referenced by a stored URL."""
        if not is_managed_media_url(file_url):
            return None
        return await self.read_managed_file(PurePosixPath(file_url).name)

    async def _read_validated_upload(self, file: UploadFile, ext: str) -> tuple[bytes, bytes]:
        chunks: list[bytes] = []
        signature = bytearray()
        total_size = 0
        while chunk := await file.read(1024 * 1024):
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                raise ValidationError("File size exceeds 10MB limit")
            if len(signature) < 12:
                signature.extend(chunk[: 12 - len(signature)])
            chunks.append(chunk)
        content = b"".join(chunks)
        if not ALLOWED_SIGNATURES[ext](bytes(signature)):
            raise ValidationError("File contents do not match the selected image or video type")
        return content, bytes(signature)


storage_service = StorageService()
