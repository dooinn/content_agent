"""Asset storage. Graph state only ever holds keys like 'projects/<id>/audio/narration.mp3'."""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import Any

from app.config import Settings


class Storage(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    async def get(self, key: str) -> bytes: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    def url(self, key: str) -> str:
        """A URL the frontend can load."""

    async def put_json(self, key: str, value: Any) -> None:
        await self.put(key, json.dumps(value, indent=2).encode(), "application/json")

    async def get_json(self, key: str, default: Any = None) -> Any:
        if not await self.exists(key):
            return default
        return json.loads(await self.get(key))


class LocalStorage(Storage):
    def __init__(self, root: Path, url_prefix: str = "/files"):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.url_prefix = url_prefix

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

    def url(self, key: str) -> str:
        return f"{self.url_prefix}/{key}"


class GCSStorage(Storage):
    def __init__(self, bucket: str):
        from google.cloud import storage

        self.bucket = storage.Client().bucket(bucket)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        blob = self.bucket.blob(key)
        await asyncio.to_thread(blob.upload_from_string, data, content_type=content_type)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self.bucket.blob(key).download_as_bytes)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self.bucket.blob(key).exists)

    def url(self, key: str) -> str:
        return self.bucket.blob(key).generate_signed_url(
            version="v4", expiration=timedelta(hours=1), method="GET"
        )


def build_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "gcs":
        return GCSStorage(settings.gcs_bucket)
    return LocalStorage(settings.local_storage_dir)
