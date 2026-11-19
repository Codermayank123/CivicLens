from urllib.parse import parse_qs, urlparse

import pytest

from app.api.v1 import media as media_api
from app.services.storage_service import signed_media_url


@pytest.mark.asyncio
async def test_signed_media_is_served_without_public_static_path(client, tmp_path, monkeypatch):
    filename = "0123456789abcdef0123456789abcdef.png"
    complaint_uploads = tmp_path / "complaints"
    complaint_uploads.mkdir()
    (complaint_uploads / filename).write_bytes(b"private evidence")
    monkeypatch.setattr(media_api, "UPLOAD_DIR", tmp_path)

    signed_url = signed_media_url(f"/uploads/complaints/{filename}")
    parsed = urlparse(signed_url)
    query = {key: values[0] for key, values in parse_qs(parsed.query).items()}

    response = await client.get(f"/api/v1/media/files/{filename}", params=query)
    assert response.status_code == 200
    assert response.content == b"private evidence"

    invalid_response = await client.get(
        f"/api/v1/media/files/{filename}",
        params={**query, "signature": "0" * 64},
    )
    assert invalid_response.status_code == 403

    public_response = await client.get(f"/uploads/complaints/{filename}")
    assert public_response.status_code == 404