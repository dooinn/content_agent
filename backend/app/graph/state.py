from dataclasses import dataclass
from typing import Any, TypedDict

from app.config import Settings


class ProjectState(TypedDict, total=False):
    """Graph state. Values are JSON-compatible dumps of app.domain.models."""

    project_id: str
    topic: str
    status: str
    feedback: str | None

    fact_sheet: dict
    eligibility: dict
    angles: list[dict]
    selected_angle: dict
    script: dict
    fact_checks: dict[str, dict]

    voice_id: str | None
    audio_targets: list[str] | None
    narration: dict
    bgm: dict

    style_ref_key: str | None
    bible: dict
    bible_image_only: bool | None
    character_refs: dict[str, str]

    scenes: list[dict]
    critic_report: dict | None
    critic_rounds: int

    keyframes: dict[str, list[str]]
    selected_keyframes: dict[str, int]
    regen_orders: list[int] | None

    preview_key: str

    clips: dict[str, list[str]]
    selected_clips: dict[str, int]
    clip_errors: dict[str, str]
    regen_clip_orders: list[int] | None
    final_key: str


@dataclass
class Deps:
    """External services the pipeline talks to; swapped for fakes in tests."""

    settings: Settings
    claude: Any
    magnific: Any
    tts: Any
    storage: Any
    renderer: Any
