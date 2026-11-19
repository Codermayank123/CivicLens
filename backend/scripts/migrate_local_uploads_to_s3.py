"""
Upload existing local complaint media to S3-compatible object storage.

Safe to re-run: skips keys that already exist in the bucket.

Usage (from backend/):
  STORAGE_BACKEND=s3 python scripts/migrate_local_uploads_to_s3.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.storage_backends import LocalStorageBackend, S3StorageBackend
from app.services.storage_service import UPLOAD_DIR


async def main() -> None:
    settings = get_settings()
    if settings.STORAGE_BACKEND != "s3":
        print("Set STORAGE_BACKEND=s3 before running this migration.")
        sys.exit(1)

    local = LocalStorageBackend(UPLOAD_DIR)
    remote = S3StorageBackend(settings)
    complaints_dir = UPLOAD_DIR / "complaints"
    if not complaints_dir.is_dir():
        print("No local uploads/complaints directory found; nothing to migrate.")
        return

    migrated = 0
    skipped = 0
    for path in sorted(complaints_dir.iterdir()):
        if not path.is_file():
            continue
        key = f"complaints/{path.name}"
        if await remote.object_exists(key):
            skipped += 1
            continue
        content = await local.get_object(key)
        if content is None:
            continue
        await remote.put_object(key, content)
        migrated += 1
        print(f"Uploaded {key}")

    print(f"Migration complete. uploaded={migrated} skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(main())
