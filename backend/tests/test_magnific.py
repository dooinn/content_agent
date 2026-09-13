import base64
import json

import httpx
import pytest

from app.services.magnific import (
    GPT_IMAGE,
    GPT_IMAGE_EDIT,
    KLING_V3,
    KLING_V3_TURBO,
    SEEDREAM_EDIT,
    UPLOADS,
    MagnificClient,
    MagnificError,
)

API_HOST = "api.magnific.com"


def client_with(handler) -> MagnificClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return MagnificClient("key", poll_interval=0, http=http)


def task(status: str, generated: list[str] | None = None) -> httpx.Response:
    return httpx.Response(200, json={"data": {"task_id": "t1", "status": status,
                                              "generated": generated or []}})


async def test_submits_polls_and_downloads():
    calls = []
    polls = iter(["IN_PROGRESS", "COMPLETED"])

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.host == "cdn.test":
            return httpx.Response(200, content=b"image-bytes")
        assert request.headers["x-magnific-api-key"] == "key"
        if request.method == "POST":
            assert b"reference_images" in request.read()
            return task("CREATED")
        status = next(polls)
        return task(status, ["https://cdn.test/out.png"] if status == "COMPLETED" else [])

    images = await client_with(handler).seedream("a knight", reference_images=["b64"])

    assert images == [b"image-bytes"]
    assert calls[0] == ("POST", SEEDREAM_EDIT)
    assert calls[1:3] == [("GET", f"{SEEDREAM_EDIT}/t1")] * 2


async def test_failed_task_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return task("CREATED" if request.method == "POST" else "FAILED")

    with pytest.raises(MagnificError, match="failed"):
        await client_with(handler).music("calm strings", 30)


async def test_client_errors_are_not_retried():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, json={"message": "bad prompt"})

    with pytest.raises(MagnificError, match="400"):
        await client_with(handler).gpt_image("x")
    assert attempts == 1


async def test_generation_posts_are_not_retried_on_ambiguous_server_errors():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, text="upstream error")

    with pytest.raises(MagnificError, match="500"):
        await client_with(handler).gpt_image("x")
    assert attempts == 1  # a retry could create and bill a second task


async def test_gpt_image_uses_edit_endpoint_only_with_references():
    posts = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "cdn.test":
            return httpx.Response(200, content=b"img")
        if request.method == "POST":
            posts.append((request.url.path, json.loads(request.read())))
            return task("CREATED")
        return task("COMPLETED", ["https://cdn.test/a.png", "https://cdn.test/b.png"])

    client = client_with(handler)
    assert await client.gpt_image("boy king", ["b64char", "b64style"], count=2) == [b"img"] * 2
    await client.gpt_image("empty hall")

    (edit_path, edit_body), (gen_path, gen_body) = posts
    assert edit_path == GPT_IMAGE_EDIT and gen_path == GPT_IMAGE
    assert edit_body["reference_images"] == ["b64char", "b64style"]
    assert edit_body["num_images"] == 2 and edit_body["aspect_ratio"] == "social_story_9_16"
    assert "reference_images" not in gen_body


async def test_kling_pro_uploads_the_frame_and_polls_the_shared_status_path():
    api_calls = []
    upload = {
        "file_id": "upl_img_1",
        "upload_url": "https://storage.test/put",
        "headers": {"Content-Type": "image/png", "x-goog-content-length-range": "0,1073741824"},
        "expires_in": 120,
        "asset_url": "https://cdn.test/frame.png",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "storage.test":
            assert request.method == "PUT" and request.read() == b"frame"
            assert request.headers["x-goog-content-length-range"] == "0,1073741824"
            assert "x-magnific-api-key" not in request.headers
            return httpx.Response(200)
        if request.url.host == "cdn.test":
            return httpx.Response(200, content=b"mp4")
        api_calls.append((request.method, request.url.path))
        if request.url.path == UPLOADS:
            return httpx.Response(200, json={"files": [upload]})
        if request.method == "POST":
            body = json.loads(request.read())
            assert body["start_image_url"] == "https://cdn.test/frame.png"
            assert body["duration"] == "7" and body["aspect_ratio"] == "9:16"
            assert body["generate_audio"] is False and body["negative_prompt"] == "blur"
            return task("CREATED")
        return task("COMPLETED", ["https://cdn.test/clip.mp4"])

    videos = await client_with(handler).image_to_video(
        "kling-v3-pro", b"frame", "image/png", "slow push-in", 7, "blur"
    )

    assert videos == [b"mp4"]
    assert api_calls == [
        ("POST", UPLOADS), ("POST", f"{KLING_V3}-pro"), ("GET", f"{KLING_V3}/t1"),
    ]


async def test_kling_turbo_sends_base64_and_clamps_duration():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "cdn.test":
            return httpx.Response(200, content=b"mp4")
        if request.method == "POST":
            assert request.url.path == f"{KLING_V3_TURBO}-1080p"
            body = json.loads(request.read())
            assert body["image"] == base64.b64encode(b"frame").decode()
            assert body["duration"] == "3"
            return task("CREATED")
        assert request.url.path == f"{KLING_V3_TURBO}/t1"
        return task("COMPLETED", ["https://cdn.test/clip.mp4"])

    client = client_with(handler)
    assert await client.image_to_video("kling-v3-turbo", b"frame", "image/png", "sway", 2) == [
        b"mp4"
    ]


async def test_kling_rejects_oversized_frames_before_uploading():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request expected")

    with pytest.raises(MagnificError, match="10 MB"):
        await client_with(handler).image_to_video(
            "kling-v3-std", b"x" * (10 * 1024 * 1024 + 1), "image/png", "sway", 5
        )
