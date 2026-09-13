"""Magnific API client (formerly Freepik API).

Generation endpoints are async: POST creates a task, and a status endpoint reports
CREATED | IN_PROGRESS | COMPLETED | FAILED with result URLs in `generated`. Most models poll at
the POST path plus /<task-id>; the Kling 3 tiers share one status path per family.
Locally we poll; webhooks replace polling once the API has a public URL.
"""

import asyncio
import base64
import time

import httpx

GPT_IMAGE = "/v1/ai/text-to-image/gpt-image-2"
GPT_IMAGE_EDIT = "/v1/ai/text-to-image/gpt-image-2-edit"
SEEDREAM = "/v1/ai/text-to-image/seedream-v4-5"
SEEDREAM_EDIT = "/v1/ai/text-to-image/seedream-v4-5-edit"
MUSIC = "/v1/ai/music-generation"
UPLOADS = "/v1/ai/uploads/request-url"
KLING_V3 = "/v1/ai/video/kling-v3"  # POST {KLING_V3}-pro|-std, GET {KLING_V3}/<task-id>
KLING_V3_TURBO = "/v1/ai/image-to-video/kling-v3-turbo"  # POST ...-1080p, GET .../<task-id>

VERTICAL = "social_story_9_16"
KLING_MAX_IMAGE_BYTES = 10 * 1024 * 1024
RETRYABLE_GET = {429, 500, 502, 503, 504}
# A POST that failed with 500/502/504 may still have created a billed task, so only retry
# responses that mean the request was not accepted.
RETRYABLE_POST = {429, 503}


class MagnificError(RuntimeError):
    pass


class MagnificClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.magnific.com",
        poll_interval: float = 4.0,
        task_timeout: float = 600.0,
        video_task_timeout: float = 1200.0,
        http: httpx.AsyncClient | None = None,
    ):
        self.poll_interval = poll_interval
        self.task_timeout = task_timeout
        self.video_task_timeout = video_task_timeout
        self.http = http or httpx.AsyncClient(timeout=120.0)
        self.base_url = base_url.rstrip("/")
        self.headers = {"x-magnific-api-key": api_key}

    async def aclose(self) -> None:
        await self.http.aclose()

    # ------------------------------------------------------------ images and music

    async def gpt_image(
        self,
        prompt: str,
        reference_images: list[str] | None = None,
        count: int = 1,
        quality: str = "high",
        aspect_ratio: str = VERTICAL,
    ) -> list[bytes]:
        """GPT Image 2; with reference images (base64 or URLs) it composes from them."""
        body: dict = {
            "prompt": prompt, "num_images": count, "quality": quality, "resolution": "2k",
            "aspect_ratio": aspect_ratio, "output_format": "png",
        }
        if reference_images:
            body["reference_images"] = reference_images[:16]
            return await self._generate(GPT_IMAGE_EDIT, body)
        return await self._generate(GPT_IMAGE, body)

    async def seedream(
        self, prompt: str, reference_images: list[str] | None = None, aspect_ratio: str = VERTICAL
    ) -> list[bytes]:
        """Text-to-image, or reference-guided when images (base64 or URLs) are given."""
        body: dict = {"prompt": prompt, "aspect_ratio": aspect_ratio}
        if reference_images:
            body["reference_images"] = reference_images[:5]
            return await self._generate(SEEDREAM_EDIT, body)
        return await self._generate(SEEDREAM, body)

    async def music(self, prompt: str, seconds: int) -> list[bytes]:
        seconds = max(10, min(240, seconds))
        return await self._generate(MUSIC, {"prompt": prompt, "music_length_seconds": seconds})

    # ------------------------------------------------------------ video

    async def image_to_video(
        self,
        model: str,
        image: bytes,
        content_type: str,
        prompt: str,
        seconds: int,
        negative_prompt: str = "",
    ) -> list[bytes]:
        """Animate a first-frame image with Kling 3 and return MP4 bytes, without audio."""
        duration = str(max(3, min(15, seconds)))
        if model == "kling-v3-turbo":
            body = {"image": base64.b64encode(image).decode(), "prompt": prompt,
                    "duration": duration}
            return await self._generate(
                f"{KLING_V3_TURBO}-1080p", body, KLING_V3_TURBO, self.video_task_timeout
            )
        if model not in ("kling-v3-pro", "kling-v3-std"):
            raise ValueError(f"unsupported video model: {model}")
        if len(image) > KLING_MAX_IMAGE_BYTES:
            raise MagnificError("Kling 3 accepts first-frame images up to 10 MB")
        body = {
            "start_image_url": await self.upload(image, content_type),
            "prompt": prompt, "duration": duration, "aspect_ratio": "9:16",
            "generate_audio": False,
        }
        if negative_prompt:
            body["negative_prompt"] = negative_prompt
        tier = model.removeprefix("kling-v3-")
        return await self._generate(f"{KLING_V3}-{tier}", body, KLING_V3, self.video_task_timeout)

    async def upload(self, data: bytes, content_type: str) -> str:
        """Stage a local file on Magnific storage; returns a public URL valid for about a day."""
        body = await self._request(
            "POST", UPLOADS, unwrap=False, json={"files": [{"content_type": content_type}]}
        )
        upload = body["files"][0]
        # The signed URL goes straight to storage: send its required headers, not the API key.
        response = await self.http.put(
            upload["upload_url"], content=data, headers=upload["headers"]
        )
        if response.is_error:
            raise MagnificError(f"upload failed {response.status_code}: {response.text[:300]}")
        return upload["asset_url"]

    # ------------------------------------------------------------ task plumbing

    async def _generate(
        self, path: str, body: dict, status_path: str | None = None, timeout: float | None = None
    ) -> list[bytes]:
        task = await self._request("POST", path, json=body)
        urls = await self._wait(status_path or path, task["task_id"], timeout or self.task_timeout)
        return list(await asyncio.gather(*(self._download(u) for u in urls)))

    async def _wait(self, path: str, task_id: str, timeout: float) -> list[str]:
        deadline = time.monotonic() + timeout
        while True:
            task = await self._request("GET", f"{path}/{task_id}")
            status = task.get("status")
            if status == "COMPLETED":
                if not task.get("generated"):
                    raise MagnificError(f"task {task_id} completed without output")
                return task["generated"]
            if status == "FAILED":
                raise MagnificError(f"task {task_id} failed")
            if time.monotonic() > deadline:
                raise MagnificError(f"task {task_id} timed out ({status})")
            await asyncio.sleep(self.poll_interval)

    async def _request(self, method: str, path: str, unwrap: bool = True, **kwargs) -> dict:
        retryable = RETRYABLE_POST if method == "POST" else RETRYABLE_GET
        for attempt in range(4):
            response = await self.http.request(
                method, f"{self.base_url}{path}", headers=self.headers, **kwargs
            )
            if response.status_code not in retryable or attempt == 3:
                break
            await asyncio.sleep(2**attempt)
        if response.is_error:
            raise MagnificError(f"{method} {path} -> {response.status_code}: {response.text[:500]}")
        body = response.json()
        return body["data"] if unwrap else body

    async def _download(self, url: str) -> bytes:
        response = await self.http.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content
