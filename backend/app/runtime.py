"""Runs graph invocations in the background and tracks project status."""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Literal

from langgraph.types import Command
from pydantic import BaseModel

from app.domain.models import GateDecision
from app.observability import flush, project_trace
from app.services.storage import Storage

logger = logging.getLogger(__name__)

Status = Literal[
    "running", "awaiting_review", "failed", "rejected", "preview_ready", "final_ready", "done"
]


class ProjectRecord(BaseModel):
    id: str
    topic: str
    status: Status
    stage: str | None = None
    error: str | None = None
    thumbnail_key: str | None = None
    created_at: datetime
    updated_at: datetime


def pick_thumbnail(values: dict) -> str | None:
    """The first scene's chosen keyframe, else a character sheet."""
    keyframes = (values.get("keyframes") or {}).get("1")
    if keyframes:
        return keyframes[(values.get("selected_keyframes") or {}).get("1", 0)]
    refs = values.get("character_refs") or {}
    return next(iter(refs.values()), None)


class ProjectRegistry:
    """Project index stored next to the assets. Fine for a single-user tool."""

    KEY = "projects/index.json"

    def __init__(self, storage: Storage):
        self.storage = storage
        self._lock = asyncio.Lock()

    async def list(self) -> list[ProjectRecord]:
        raw = await self.storage.get_json(self.KEY, default={})
        records = [ProjectRecord.model_validate(r) for r in raw.values()]
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    async def get(self, project_id: str) -> ProjectRecord | None:
        raw = await self.storage.get_json(self.KEY, default={})
        return ProjectRecord.model_validate(raw[project_id]) if project_id in raw else None

    async def save(self, record: ProjectRecord) -> None:
        async with self._lock:
            raw = await self.storage.get_json(self.KEY, default={})
            raw[record.id] = record.model_dump(mode="json")
            await self.storage.put_json(self.KEY, raw)


class ProjectRunner:
    def __init__(self, graph, registry: ProjectRegistry):
        self.graph = graph
        self.registry = registry
        self._tasks: dict[str, asyncio.Task] = {}

    @staticmethod
    def config(project_id: str) -> dict:
        return {"configurable": {"thread_id": project_id}}

    def is_running(self, project_id: str) -> bool:
        task = self._tasks.get(project_id)
        return task is not None and not task.done()

    async def snapshot(self, project_id: str):
        return await self.graph.aget_state(self.config(project_id))

    async def create(
        self,
        topic: str,
        voice_id: str | None,
        style_ref_key: str | None = None,
        options: dict | None = None,
    ) -> ProjectRecord:
        """`options` may carry image_model, image_quality, video_model, and caption_style."""
        now = datetime.now(UTC)
        record = ProjectRecord(
            id=uuid.uuid4().hex[:12], topic=topic, status="running", stage="research",
            created_at=now, updated_at=now,
        )
        await self.registry.save(record)
        self._launch(record.id, {
            "project_id": record.id, "topic": topic, "voice_id": voice_id,
            "style_ref_key": style_ref_key, **(options or {}),
        })
        return record

    async def decide(self, project_id: str, decision: GateDecision) -> None:
        self._launch(project_id, Command(resume=decision.model_dump()))

    async def retry(self, project_id: str) -> None:
        # Invoking with None resumes from the last checkpoint and re-runs the failed node.
        self._launch(project_id, None)

    def _launch(self, project_id: str, graph_input) -> None:
        self._tasks[project_id] = asyncio.create_task(self._run(project_id, graph_input))

    async def _run(self, project_id: str, graph_input) -> None:
        record = await self.registry.get(project_id)
        record.status, record.error = "running", None
        await self.registry.save(record)
        try:
            with project_trace(project_id, record.stage or "start"):
                await self.graph.ainvoke(graph_input, self.config(project_id))
            snap = await self.snapshot(project_id)
            record.thumbnail_key = pick_thumbnail(snap.values) or record.thumbnail_key
            if snap.interrupts:
                record.status, record.stage = "awaiting_review", snap.interrupts[0].value["stage"]
            else:
                record.status, record.stage = snap.values.get("status", "done"), None
        except Exception as exc:
            logger.exception("project %s failed", project_id)
            record.status, record.error = "failed", f"{type(exc).__name__}: {exc}"
        finally:
            flush()
        record.updated_at = datetime.now(UTC)
        await self.registry.save(record)
