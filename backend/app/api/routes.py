import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.config import ImageModel, ImageQuality, VideoModel, get_settings
from app.domain.models import CaptionStyle, GateDecision
from app.graph.pipeline import validate_decision
from app.runtime import ProjectRecord, ProjectRunner, pick_thumbnail
from app.services.fonts import FONTS
from app.services.media import image_type

router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ASSET_PREFIXES = ("projects/", "uploads/")

IMAGE_MODELS = [
    {
        "id": "gpt-image-2",
        "label": "GPT Image 2",
        "note": "Strong prompt adherence and reference consistency",
    },
    {"id": "seedream", "label": "Seedream 4.5", "note": "Alternative image model"},
]
VIDEO_MODELS = [
    {"id": "kling-v3-pro", "label": "Kling 3 Pro", "note": "Highest fidelity"},
    {"id": "kling-v3-std", "label": "Kling 3 Standard", "note": "720p output, lower cost"},
    {"id": "kling-v3-turbo", "label": "Kling 3 Turbo", "note": "1080p output, fastest"},
]
CAPTION_POSITIONS = [
    {"id": "bottom", "label": "Bottom"},
    {"id": "lower-third", "label": "Lower third"},
    {"id": "center", "label": "Center"},
]


class CreateProject(BaseModel):
    topic: str = Field(min_length=2, max_length=200, examples=["Napoleon Bonaparte"])
    voice_id: str | None = None
    style_ref_key: str | None = Field(
        default=None, description="Key returned by POST /uploads; sets the visual style."
    )
    image_model: ImageModel | None = None
    image_quality: ImageQuality | None = None
    video_model: VideoModel | None = None
    caption_style: CaptionStyle | None = None


class ProjectSummary(ProjectRecord):
    thumbnail_url: str | None = None


class ProjectView(BaseModel):
    project: ProjectRecord
    running: bool
    stage: str | None
    payload: dict | None
    state: dict
    assets: dict[str, str] = Field(description="Storage key -> URL the browser can load.")


def _runner(request: Request) -> ProjectRunner:
    return request.app.state.runner


def _asset_keys(value: Any) -> set[str]:
    if isinstance(value, str):
        is_file = value.startswith(ASSET_PREFIXES) and "." in value.rsplit("/", 1)[-1]
        return {value} if is_file else set()
    if isinstance(value, dict):
        return set().union(*map(_asset_keys, value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*map(_asset_keys, value)) if value else set()
    return set()


async def _record_or_404(runner: ProjectRunner, project_id: str) -> ProjectRecord:
    record = await runner.registry.get(project_id)
    if record is None:
        raise HTTPException(404, "project not found")
    return record


async def _require_upload(runner: ProjectRunner, key: str | None) -> None:
    if key is None:
        return
    if not key.startswith("uploads/") or not await runner.registry.storage.exists(key):
        raise HTTPException(422, f"unknown upload key: {key}")


@router.get("/health")
async def health() -> dict:
    return {"ok": True}


@router.get("/options")
async def options() -> dict:
    """Choices the console offers, with the server defaults."""
    settings = get_settings()
    return {
        "image_models": IMAGE_MODELS,
        "image_qualities": ["low", "medium", "high"],
        "video_models": VIDEO_MODELS,
        "caption_fonts": [{"id": font.id, "label": font.label} for font in FONTS.values()],
        "caption_positions": CAPTION_POSITIONS,
        "caption_size": {"min": 48, "max": 140},
        "defaults": {
            "image_model": settings.image_model,
            "image_quality": settings.image_quality,
            "video_model": settings.video_model,
            "caption_style": CaptionStyle().model_dump(),
        },
    }


@router.post("/uploads", status_code=201)
async def upload_image(file: UploadFile, request: Request) -> dict:
    """Upload a reference image (PNG, JPEG, or WebP, up to 10 MB)."""
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "image is larger than 10 MB")
    kind = image_type(data)
    if kind is None:
        raise HTTPException(415, "upload a PNG, JPEG, or WebP image")
    key = f"uploads/{uuid.uuid4().hex}.{kind[0]}"
    storage = _runner(request).registry.storage
    await storage.put(key, data, kind[1])
    return {"key": key, "url": storage.url(key)}


@router.post("/projects", status_code=202)
async def create_project(body: CreateProject, request: Request) -> ProjectRecord:
    runner = _runner(request)
    await _require_upload(runner, body.style_ref_key)
    options = body.model_dump(
        include={"image_model", "image_quality", "video_model", "caption_style"}, exclude_none=True
    )
    return await runner.create(body.topic, body.voice_id, body.style_ref_key, options)


@router.get("/projects")
async def list_projects(request: Request) -> list[ProjectSummary]:
    runner = _runner(request)
    storage = runner.registry.storage
    summaries = []
    for record in await runner.registry.list():
        # Projects indexed before thumbnails existed get one from their checkpoint, once.
        if record.thumbnail_key is None and not runner.is_running(record.id):
            snap = await runner.snapshot(record.id)
            if key := pick_thumbnail(snap.values):
                record.thumbnail_key = key
                await runner.registry.save(record)
        url = storage.url(record.thumbnail_key) if record.thumbnail_key else None
        summaries.append(ProjectSummary(**record.model_dump(), thumbnail_url=url))
    return summaries


@router.get("/projects/{project_id}")
async def get_project(project_id: str, request: Request) -> ProjectView:
    runner = _runner(request)
    record = await _record_or_404(runner, project_id)
    snap = await runner.snapshot(project_id)
    pending = snap.interrupts[0].value if snap.interrupts else None
    storage = runner.registry.storage
    return ProjectView(
        project=record,
        running=runner.is_running(project_id),
        stage=pending["stage"] if pending else None,
        payload=pending["payload"] if pending else None,
        state=snap.values,
        assets={key: storage.url(key) for key in sorted(_asset_keys(snap.values))},
    )


@router.post("/projects/{project_id}/decisions", status_code=202)
async def decide(project_id: str, decision: GateDecision, request: Request) -> dict:
    runner = _runner(request)
    await _record_or_404(runner, project_id)
    if runner.is_running(project_id):
        raise HTTPException(409, "project is still running")
    snap = await runner.snapshot(project_id)
    if not snap.interrupts:
        raise HTTPException(409, "nothing is awaiting review")
    stage = snap.interrupts[0].value["stage"]
    if error := validate_decision(stage, decision, snap.values):
        raise HTTPException(422, error)
    await _require_upload(runner, decision.edits.get("style_ref_key"))
    await runner.decide(project_id, decision)
    return {"accepted": True, "stage": stage}


@router.post("/projects/{project_id}/retry", status_code=202)
async def retry(project_id: str, request: Request) -> dict:
    runner = _runner(request)
    record = await _record_or_404(runner, project_id)
    if record.status != "failed" or runner.is_running(project_id):
        raise HTTPException(409, "only failed projects can be retried")
    await runner.retry(project_id)
    return {"accepted": True}


@router.get("/graph", response_class=PlainTextResponse)
async def graph_diagram(request: Request) -> str:
    """Mermaid diagram of the pipeline."""
    return _runner(request).graph.get_graph().draw_mermaid()
