import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.domain.models import GateDecision
from app.graph.pipeline import validate_decision
from app.runtime import ProjectRecord, ProjectRunner
from app.services.media import image_type

router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ASSET_PREFIXES = ("projects/", "uploads/")


class CreateProject(BaseModel):
    topic: str = Field(min_length=2, max_length=200, examples=["Napoleon Bonaparte"])
    voice_id: str | None = None
    style_ref_key: str | None = Field(
        default=None, description="Key returned by POST /uploads; sets the visual style."
    )


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
    return await runner.create(body.topic, body.voice_id, body.style_ref_key)


@router.get("/projects")
async def list_projects(request: Request) -> list[ProjectRecord]:
    return await _runner(request).registry.list()


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
