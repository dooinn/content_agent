"""Domain models.

LLM-facing models are used as structured-output schemas, so every field carries a
description the model can read. Graph state stores their JSON dumps, not instances.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

Beat = Literal["hook", "setup", "twist", "payoff", "closer"]


# ---------------------------------------------------------------- research


class Source(BaseModel):
    id: str = Field(description="Source id from the provided source list, e.g. 'S3'.")
    title: str
    url: str
    tier: Literal["scholarly", "reference", "popular"] = Field(
        description="scholarly: peer-reviewed journals, academic books, university presses. "
        "reference: major encyclopedias, museums, archives, official heritage sites, established "
        "history publishers. popular: blogs, listicles, Q&A sites, social media, fan wikis, "
        "content farms."
    )


class Fact(BaseModel):
    id: str = Field(description="Stable id, e.g. 'F1'.")
    claim: str = Field(description="One self-contained factual claim.")
    status: Literal["verified", "disputed", "legend"] = Field(
        description="verified: clearly supported by a scholarly or reference source. disputed: "
        "historians disagree or evidence is thin. legend: popular story without solid evidence."
    )
    source_ids: list[str]
    note: str = Field(default="", description="Caveats, competing accounts, or context.")


class FactSheet(BaseModel):
    figure: str = Field(description="Commonly used English name.")
    born: str = Field(description="Birth date or year as precisely as known.")
    died: str = Field(description="Death date or year, or 'living'.")
    death_year: int | None = Field(description="Death year as an integer; null if living/unknown.")
    era: str
    region: str
    summary: str = Field(description="Two-sentence biography.")
    appearance_notes: str = Field(
        description="How the person looked, per portraits or contemporary descriptions."
    )
    costume_notes: str = Field(description="Period-accurate clothing, hair, accessories.")
    setting_notes: str = Field(description="Architecture, objects, landscapes of their world.")
    facts: list[Fact]
    sources: list[Source]


class FactCheckIssue(BaseModel):
    location: str = Field(description="Where the claim appears, e.g. 'angle 2 hook_line'.")
    claim: str
    problem: Literal["not_in_fact_sheet", "contradicts_fact_sheet", "overstates_certainty"]
    suggested_fix: str


class FactCheckReport(BaseModel):
    passed: bool
    issues: list[FactCheckIssue]


class StoryAngle(BaseModel):
    title: str
    hook_line: str = Field(description="Opening line, max 12 words, creates curiosity.")
    logline: str = Field(description="The whole story in two sentences.")
    fact_ids: list[str]
    why_it_works: str
    accuracy_notes: str = Field(description="How disputed or legendary elements are handled.")


class AngleOptions(BaseModel):
    angles: list[StoryAngle]


# ---------------------------------------------------------------- script


class ScriptSegment(BaseModel):
    beat: Beat
    narration: str = Field(description="Spoken text for one scene, 8-16 words.")
    fact_ids: list[str]


class Script(BaseModel):
    title: str
    segments: list[ScriptSegment]

    @property
    def full_text(self) -> str:
        return " ".join(s.narration.strip() for s in self.segments)

    @property
    def word_count(self) -> int:
        return len(self.full_text.split())


# ---------------------------------------------------------------- audio


class WordTiming(BaseModel):
    text: str
    start: float
    end: float


class SegmentTiming(BaseModel):
    order: int
    start: float
    end: float


class Narration(BaseModel):
    audio_key: str
    voice_id: str
    duration: float
    words: list[WordTiming]
    segments: list[SegmentTiming]


class MusicBrief(BaseModel):
    prompt: str = Field(description="Prompt for an instrumental track, max 400 characters.")


class Bgm(BaseModel):
    audio_key: str
    prompt: str
    seconds: int


# ---------------------------------------------------------------- visuals


class CharacterLook(BaseModel):
    id: str = Field(description="Short lowercase slug, e.g. 'young' or 'mature'.")
    label: str = Field(description="e.g. 'Louis at fourteen, dancing Apollo'.")
    age: str
    physical_description: str
    costume: str
    sheet_prompt: str = Field(
        description="Prompt for one vertical full-body reference image of this look."
    )


class CharacterSpec(BaseModel):
    name: str
    signature_props: list[str]
    looks: list[CharacterLook] = Field(
        description="One look per clearly different age or costume shown on screen. Most "
        "stories need exactly one."
    )


class StyleBible(BaseModel):
    visual_style: str = Field(description="One consistent look for every scene.")
    color_palette: str
    lighting: str
    period_details: list[str] = Field(description="Details that make the era feel authentic.")
    anachronisms_to_avoid: list[str]
    character: CharacterSpec


class SceneDraft(BaseModel):
    order: int = Field(description="Matches the narration segment order, starting at 1.")
    description: str
    shot_type: str = Field(description="e.g. extreme close-up, medium shot, wide establishing.")
    camera_move: str = Field(description="Subtle move for later animation, e.g. slow push-in.")
    character_look: str | None = Field(
        description="id of the character look visible in this scene, or null if the character "
        "is not shown."
    )
    image_prompt: str


class SceneSet(BaseModel):
    scenes: list[SceneDraft]


class MotionShot(BaseModel):
    order: int = Field(description="Scene order, starting at 1.")
    video_prompt: str = Field(description="Motion and camera direction for this scene's clip.")


class MotionPlan(BaseModel):
    shots: list[MotionShot]


class CriticIssue(BaseModel):
    scene_order: int
    category: Literal[
        "anachronism", "continuity", "fact_mismatch", "character_reference", "bible_rule",
        "prompt_quality", "safety",
    ]
    detail: str
    suggested_fix: str


class CriticReport(BaseModel):
    passed: bool
    issues: list[CriticIssue]


# ---------------------------------------------------------------- review gates


class GateDecision(BaseModel):
    """What the reviewer sends back to resume a paused stage."""

    action: Literal["approve", "revise", "select", "regenerate"]
    feedback: str | None = None
    choice: int | None = None
    scene_orders: list[int] = Field(default_factory=list)
    edits: dict[str, Any] = Field(default_factory=dict)
