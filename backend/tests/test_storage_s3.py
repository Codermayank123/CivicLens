"""Object storage backend tests."""

import pytest

from app.services.storage_backends import LocalStorageBackend, S3StorageBackend, media_url_to_object_key
from app.services.storage_service import StorageService
from app.config import Settings


def test_media_url_to_object_key():
    assert media_url_to_object_key("/uploads/complaints/0123456789abcdef0123456789abcdef.png") == (
        "complaints/0123456789abcdef0123456789abcdef.png"
    )


@pytest.mark.asyncio
async def test_storage_service_round_trip_local(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage_service.UPLOAD_DIR", tmp_path / "uploads")
    backend = LocalStorageBackend(tmp_path / "uploads")
    service = StorageService(backend=backend)

    class FakeUpload:
        filename = "photo.png"
        size = 8
        _sent = False

        async def read(self, n=-1):
            if self._sent:
                return b""
            self._sent = True
            return b"\x89PNG\r\n\x1a\n" + b"1234567890"

    url = await service.save_file(FakeUpload())  # type: ignore[arg-type]
    filename = url.rsplit("/", 1)[-1]
    content = await service.read_managed_file(filename)
    assert content is not None
    assert content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_s3_backend_put_and_get(monkeypatch):
    store: dict[str, bytes] = {}

    class FakeClient:
        def put_object(self, Bucket, Key, Body):
            store[Key] = Body

        def get_object(self, Bucket, Key):
            return {"Body": _FakeBody(store[Key])}

        def head_object(self, Bucket, Key):
            if Key not in store:
                raise _ClientError("404")

        def head_bucket(self, Bucket):
            return True

    class _FakeBody:
        def __init__(self, data: bytes):
            self._data = data

        def read(self):
            return self._data

    class _ClientError(Exception):
        pass

    monkeypatch.setattr("app.services.storage_backends.boto3.client", lambda *args, **kwargs: FakeClient())
    settings = Settings(
        STORAGE_BACKEND="s3",
        S3_BUCKET_NAME="test-bucket",
        S3_ACCESS_KEY="key",
        S3_SECRET_KEY="secret",
    )
    backend = S3StorageBackend(settings)
    await backend.put_object("complaints/demo.png", b"data")
    assert await backend.get_object("complaints/demo.png") == b"data"
    assert await backend.check_connection() is True
