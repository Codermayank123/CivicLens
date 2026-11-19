"""Local disk and S3-compatible object storage backends."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath

import aiofiles
import boto3
from botocore.exceptions import ClientError

from app.config import Settings


def media_url_to_object_key(file_url: str) -> str:
    """Map `/uploads/complaints/<file>` to object key `complaints/<file>`."""
    parts = PurePosixPath(file_url).parts
    if len(parts) != 4 or parts[1] != "uploads":
        raise ValueError(f"Unsupported media URL: {file_url}")
    return f"{parts[2]}/{parts[3]}"


class StorageBackend(ABC):
    @abstractmethod
    async def put_object(self, key: str, content: bytes) -> None: ...

    @abstractmethod
    async def get_object(self, key: str) -> bytes | None: ...

    @abstractmethod
    async def object_exists(self, key: str) -> bool: ...

    @abstractmethod
    async def check_connection(self) -> bool: ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, upload_dir: Path) -> None:
        self._upload_dir = upload_dir
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def _path_for_key(self, key: str) -> Path:
        return self._upload_dir / Path(*key.split("/"))

    async def put_object(self, key: str, content: bytes) -> None:
        target = self._path_for_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(target, "wb") as handle:
            await handle.write(content)

    async def get_object(self, key: str) -> bytes | None:
        target = self._path_for_key(key)
        if not target.is_file():
            return None
        async with aiofiles.open(target, "rb") as handle:
            return await handle.read()

    async def object_exists(self, key: str) -> bool:
        return self._path_for_key(key).is_file()

    async def check_connection(self) -> bool:
        return self._upload_dir.exists()


class S3StorageBackend(StorageBackend):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )

    async def put_object(self, key: str, content: bytes) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._settings.S3_BUCKET_NAME,
            Key=key,
            Body=content,
        )

    async def get_object(self, key: str) -> bytes | None:
        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=self._settings.S3_BUCKET_NAME,
                Key=key,
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        body = response["Body"].read()
        return body

    async def object_exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._settings.S3_BUCKET_NAME,
                Key=key,
            )
            return True
        except ClientError:
            return False

    async def check_connection(self) -> bool:
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._settings.S3_BUCKET_NAME)
            return True
        except ClientError:
            return False
