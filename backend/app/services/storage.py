"""Asset storage. Graph state only ever holds keys like 'projects/<id>/audio/narration.mp3'.

The browser always loads assets from /files/<key>. Local storage serves that path directly;
with GCS the API redirects it to a short-lived signed URL, created only when a file is requested.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import Any

from app.config import Settings

URL_PREFIX = "/files"


class Storage(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    async def get(self, key: str) -> bytes: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    def url(self, key: str) -> str:
        """A URL the frontend can load."""
        return f"{URL_PREFIX}/{key}"

    async def put_json(self, key: str, value: Any) -> None:
        await self.put(key, json.dumps(value, indent=2).encode(), "application/json")

    async def get_json(self, key: str, default: Any = None) -> Any:
        if not await self.exists(key):
            return default
        return json.loads(await self.get(key))


class LocalStorage(Storage):
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"invalid key: {key}")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def exists(self, key: str) -> bool:
        return self._path(key).exists()


class GCSStorage(Storage):
    URL_LIFETIME = timedelta(hours=2)
    CACHE_SECONDS = 3600  # reuse a signed URL while it has at least an hour left

    def __init__(self, bucket: str):
        import google.auth
        from google.auth.transport.requests import Request
        from google.cloud import storage

        self._credentials, project = google.auth.default()
        self._auth_request = Request()
        self.bucket = storage.Client(credentials=self._credentials, project=project).bucket(bucket)
        self._signed: dict[str, tuple[str, float]] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        blob = self.bucket.blob(key)
        await asyncio.to_thread(blob.upload_from_string, data, content_type=content_type)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self.bucket.blob(key).download_as_bytes)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self.bucket.blob(key).exists)

    def signed_url(self, key: str) -> str:
        """Blocking; call from a thread. Cached so a polling console does not re-sign files."""
        cached = self._signed.get(key)
        if cached and cached[1] > time.monotonic():
            return cached[0]
        options: dict[str, Any] = {}
        if not hasattr(self._credentials, "sign_bytes"):
            # Cloud Run credentials have no private key, so sign through the IAM API.
            if not self._credentials.valid:
                self._credentials.refresh(self._auth_request)
            options = {
                "service_account_email": self._credentials.service_account_email,
                "access_token": self._credentials.token,
            }
        url = self.bucket.blob(key).generate_signed_url(
            version="v4", expiration=self.URL_LIFETIME, method="GET", **options
        )
        self._signed[key] = (url, time.monotonic() + self.CACHE_SECONDS)
        return url


def build_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "gcs":
        return GCSStorage(settings.gcs_bucket)
    return LocalStorage(settings.local_storage_dir)
