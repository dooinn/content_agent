"""Pipeline nodes.

Work nodes call models and store results. Gate nodes only pause for review and route; they are
kept separate because LangGraph re-runs a whole node when it resumes after interrupt().
Feedback sent with a revision reshapes the same stage; feedback sent with an approval steers
the next one.
"""

import asyncio
import base64
import math
import tempfile
import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from pathlib import Path
from typing import Literal, TypeVar, get_args

from langgraph.graph import END
from langgraph.types import Command, interrupt
from pydantic import BaseModel, ValidationError

from app.config import ImageModel, ImageQuality, VideoModel
from app.domain.length import TARGET_SECONDS, LengthProfile, length_profile
from app.domain.models import (
    AngleOptions,
    Bgm,
    CaptionStyle,
    CriticReport,
    FactCheckReport,
    FactSheet,
    GateDecision,
    MotionPlan,
    MusicBrief,
    Narration,
    SceneSet,
    Script,
    StyleBible,
)
from app.graph.state import Deps, ProjectState
from app.llm import prompts
from app.services.media import image_type
from app.services.render import SceneClip
from app.services.timing import build_timings

T = TypeVar("T", bound=BaseModel)

STAGE_ACTIONS = {
    "research": {"approve", "revise"},
    "angle": {"select", "revise"},
    "script": {"approve", "revise"},
    "audio": {"approve", "revise"},
    "bible": {"approve", "revise"},
    "scenes": {"approve", "revise"},
    "keyframes": {"approve", "regenerate"},
    "preview": {"approve", "revise", "regenerate"},
    "motion": {"approve", "revise"},
    "clips": {"approve", "regenerate"},
    "final": {"approve", "revise"},
}
SCENE_EDIT_FIELDS = {"description", "shot_type", "camera_move", "character_look", "image_prompt"}
MOTION_EDIT_FIELDS = {"video_prompt", "clip_seconds"}
SHOT_FIELDS = ("order", "narration", "video_prompt", "clip_seconds")
TRUSTED_TIERS = {"scholarly", "reference"}
MODEL_FIELDS = {
    "image_model": get_args(ImageModel),
    "image_quality": get_args(ImageQuality),
    "video_model": get_args(VideoModel),
}


def check_eligibility(sheet: FactSheet, min_years: int, today: date | None = None) -> dict:
    year = (today or date.today()).year
    if sheet.death_year is None:
        return {"ok": False, "reason": f"{sheet.figure} is living or their death year is "
                "unknown; only long-deceased historical figures are supported."}
    if year - sheet.death_year < min_years:
        return {"ok": False, "reason": f"{sheet.figure} died in {sheet.death_year}; figures "
                f"must have died at least {min_years} years ago."}
    return {"ok": True, "reason": ""}


def enforce_source_rules(sheet: FactSheet) -> FactSheet:
    """A fact stays 'verified' only if a scholarly or reference source backs it."""
    tiers = {source.id: source.tier for source in sheet.sources}
    for fact in sheet.facts:
        trusted = any(tiers.get(source_id) in TRUSTED_TIERS for source_id in fact.source_ids)
        if fact.status == "verified" and not trusted:
            fact.status = "disputed"
            fact.note = f"{fact.note} Downgraded: no scholarly or reference source.".strip()
    return sheet


def clip_seconds(scene: dict) -> int:
    """Kling takes whole seconds (3-15); round up so the clip covers the narration."""
    return max(3, min(15, math.ceil(scene["end"] - scene["start"] - 1e-6)))


def _selection_error(candidates: dict, selections: dict) -> str | None:
    for order, index in selections.items():
        if not 0 <= int(index) < len(candidates.get(str(order), [])):
            return f"selection {index} is out of range for scene {order}"
    return None


def validate_decision(stage: str, decision: GateDecision, state: dict) -> str | None:
    """Return an error message if the decision cannot be applied at this stage."""
    allowed = STAGE_ACTIONS.get(stage, set())
    if decision.action not in allowed:
        return f"'{decision.action}' is not valid at stage '{stage}'; use {sorted(allowed)}"
    if decision.action == "regenerate" and not decision.scene_orders:
        return "scene_orders is required to regenerate"
    for field, values in MODEL_FIELDS.items():
        value = decision.edits.get(field)
        if value is not None and value not in values:
            return f"{field} must be one of {list(values)}"
    if "target_seconds" in decision.edits:
        if stage != "research":
            return "target_seconds can only change at the research stage, before the story"
        if decision.edits["target_seconds"] not in TARGET_SECONDS:
            return f"target_seconds must be one of {list(TARGET_SECONDS)}"
    if "caption_style" in decision.edits:
        try:
            CaptionStyle.model_validate(decision.edits["caption_style"])
        except ValidationError as exc:
            return f"invalid caption_style: {exc.errors()[0]['msg']}"
    selections = decision.edits.get("selections", {})
    if stage == "angle" and decision.action == "select":
        if decision.choice is None or not 0 <= decision.choice < len(state["angles"]):
            return "choice must be the index of one of the proposed angles"
    if stage == "script" and "narration" in decision.edits:
        if len(decision.edits["narration"]) != len(state["script"]["segments"]):
            return "edits.narration must contain one string per segment"
    if stage == "keyframes":
        return _selection_error(state["keyframes"], selections)
    if stage == "motion":
        for shot in decision.edits.get("shots", []):
            seconds = shot.get("clip_seconds")
            if seconds is not None and not (isinstance(seconds, int) and 3 <= seconds <= 15):
                return "clip_seconds must be a whole number from 3 to 15"
    if stage == "clips" and decision.action == "approve":
        clips = state.get("clips") or {}
        missing = [s["order"] for s in state["scenes"] if not clips.get(str(s["order"]))]
        if missing:
            return f"every scene needs a clip before approval; missing scenes {missing}"
        return _selection_error(clips, selections)
    return None


def ask(stage: str, payload: dict) -> GateDecision:
    return GateDecision.model_validate(interrupt({"stage": stage, "payload": payload}))


def model_edits(decision: GateDecision) -> dict:
    """Model choices a reviewer may change right before the step that uses them."""
    return {field: decision.edits[field] for field in MODEL_FIELDS if decision.edits.get(field)}


def length_edit(decision: GateDecision) -> dict:
    target = decision.edits.get("target_seconds")
    return {"target_seconds": target} if target else {}


class Pipeline:
    def __init__(self, deps: Deps):
        self.claude = deps.claude
        self.magnific = deps.magnific
        self.tts = deps.tts
        self.storage = deps.storage
        self.renderer = deps.renderer
        self.settings = deps.settings

    # ------------------------------------------------------------------ per-project settings

    def _image_model(self, state: ProjectState) -> str:
        return state.get("image_model") or self.settings.image_model

    def _image_quality(self, state: ProjectState) -> str:
        return state.get("image_quality") or self.settings.image_quality

    def _video_model(self, state: ProjectState) -> str:
        return state.get("video_model") or self.settings.video_model

    @staticmethod
    def _length(state: ProjectState) -> LengthProfile:
        return length_profile(state.get("target_seconds"))

    @staticmethod
    def _caption_style(state: ProjectState) -> CaptionStyle:
        return CaptionStyle.model_validate(state.get("caption_style") or {})

    @classmethod
    def _caption_update(cls, state: ProjectState, decision: GateDecision) -> dict:
        if "caption_style" not in decision.edits:
            return {}
        merged = {**cls._caption_style(state).model_dump(), **decision.edits["caption_style"]}
        return {"caption_style": CaptionStyle.model_validate(merged).model_dump()}

    # ------------------------------------------------------------------ helpers

    async def _images(
        self, state: ProjectState, prompt: str, references: list[bytes], count: int
    ) -> list[bytes]:
        refs = [base64.b64encode(r).decode() for r in references] or None
        if self._image_model(state) == "gpt-image-2":
            return await self.magnific.gpt_image(
                prompt, refs, count=count, quality=self._image_quality(state)
            )
        batches = await asyncio.gather(
            *(self.magnific.seedream(prompt, refs) for _ in range(count))
        )
        return [image for batch in batches for image in batch]

    async def _style_reference(self, state: ProjectState) -> bytes | None:
        key = state.get("style_ref_key")
        return await self.storage.get(key) if key else None

    async def _store_image(self, project_id: str, folder: str, name: str, data: bytes) -> str:
        ext, content_type = image_type(data) or ("jpg", "image/jpeg")
        key = f"projects/{project_id}/{folder}/{name}-{uuid.uuid4().hex[:8]}.{ext}"
        await self.storage.put(key, data, content_type)
        return key

    async def _fact_checked(
        self,
        kind: str,
        write: Callable[[object, dict | None], Awaitable[T]],
        sheet: dict,
        previous: object,
    ) -> tuple[T, FactCheckReport, dict]:
        """Write a draft, check it against the fact sheet, and rewrite while claims fail.

        Also returns how many drafts it took and how many issues the first draft had, which is
        how often the writer invents claims before the checker catches them.
        """
        draft: T | None = None
        report: FactCheckReport | None = None
        issue_counts: list[int] = []
        for _ in range(self.settings.max_fact_rewrites + 1):
            review = report.model_dump() if report else None
            if draft is not None:
                previous = draft.model_dump()
            draft = await write(previous, review)
            report = await self.claude.generate(
                system=prompts.SYSTEM,
                prompt=prompts.fact_check(kind, draft.model_dump(), sheet),
                schema=FactCheckReport,
                effort="medium",
            )
            passed = report.passed or not report.issues
            issue_counts.append(0 if passed else len(report.issues))
            if passed:
                break
        stats = {
            "drafts": len(issue_counts),
            "issues_per_draft": issue_counts,
            "passed": issue_counts[-1] == 0,
        }
        return draft, report, stats

    @staticmethod
    def _with_fact_check(
        state: ProjectState, stage: str, report: FactCheckReport, stats: dict
    ) -> dict:
        return {
            "fact_checks": {**(state.get("fact_checks") or {}), stage: report.model_dump()},
            "fact_check_stats": {**(state.get("fact_check_stats") or {}), stage: stats},
        }

    async def _render(self, state: ProjectState, name: str, kind: Literal["image", "video"]) -> str:
        """Cut the selected keyframes (animatic) or clips (final) to the narration."""
        narration = Narration.model_validate(state["narration"])
        if kind == "image":
            assets, selected = state["keyframes"], state["selected_keyframes"]
        else:
            assets, selected = state["clips"], state["selected_clips"]
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            clips = []
            for scene, timing in zip(state["scenes"], narration.segments, strict=True):
                order = str(scene["order"])
                key = assets[order][selected[order]]
                file_name = f"scene_{int(order):02d}{Path(key).suffix}"
                (workdir / file_name).write_bytes(await self.storage.get(key))
                clips.append(
                    SceneClip(path=file_name, duration=timing.end - timing.start, kind=kind)
                )

            (workdir / "narration.mp3").write_bytes(await self.storage.get(narration.audio_key))
            bgm_name = None
            if bgm := state.get("bgm"):
                bgm_name = "bgm.mp3"
                (workdir / bgm_name).write_bytes(await self.storage.get(bgm["audio_key"]))

            output = await self.renderer.render(
                workdir, clips, "narration.mp3", bgm_name, narration.words, narration.duration,
                output=f"{name}.mp4", caption_style=self._caption_style(state),
            )
            key = f"projects/{state['project_id']}/{name}/{name}-{uuid.uuid4().hex[:8]}.mp4"
            await self.storage.put(key, output.read_bytes(), "video/mp4")
        return key

    # ------------------------------------------------------------------ research

    async def research(self, state: ProjectState) -> dict:
        found = await self.claude.research(
            system=prompts.SYSTEM,
            prompt=prompts.research(state["topic"], state.get("feedback"), self._length(state)),
        )
        sheet = await self.claude.generate(
            system=prompts.SYSTEM,
            prompt=prompts.fact_sheet(state["topic"], found.notes, found.sources),
            schema=FactSheet,
        )
        sheet = enforce_source_rules(sheet)
        return {
            "fact_sheet": sheet.model_dump(),
            "eligibility": check_eligibility(sheet, self.settings.min_years_since_death),
            "feedback": None,
        }

    def gate_research(self, state: ProjectState) -> Command:
        decision = ask(
            "research", {"fact_sheet": state["fact_sheet"], "eligibility": state["eligibility"]}
        )
        length = length_edit(decision)
        if decision.action == "revise":
            topic = decision.edits.get("topic", state["topic"])
            return Command(
                goto="research", update={"feedback": decision.feedback, "topic": topic, **length}
            )
        if not state["eligibility"]["ok"]:
            return Command(goto=END, update={"status": "rejected"})
        return Command(goto="angles", update={"feedback": decision.feedback, **length})

    # ------------------------------------------------------------------ story

    async def angles(self, state: ProjectState) -> dict:
        sheet = state["fact_sheet"]

        async def write(previous, review) -> AngleOptions:
            return await self.claude.generate(
                system=prompts.SYSTEM,
                prompt=prompts.angles(
                    sheet, state.get("feedback"), previous, review, self._length(state)
                ),
                schema=AngleOptions,
            )

        options, report, stats = await self._fact_checked(
            "set of story angles", write, sheet, state.get("angles")
        )
        return {
            "angles": [a.model_dump() for a in options.angles],
            **self._with_fact_check(state, "angles", report, stats),
            "feedback": None,
        }

    def gate_angle(self, state: ProjectState) -> Command:
        fact_check = (state.get("fact_checks") or {}).get("angles")
        decision = ask("angle", {"angles": state["angles"], "fact_check": fact_check})
        if decision.action == "select":
            angle = state["angles"][decision.choice]
            return Command(
                goto="script", update={"selected_angle": angle, "feedback": decision.feedback}
            )
        return Command(goto="angles", update={"feedback": decision.feedback})

    async def script(self, state: ProjectState) -> dict:
        sheet = state["fact_sheet"]

        async def write(previous, review) -> Script:
            return await self.claude.generate(
                system=prompts.SYSTEM,
                prompt=prompts.script(
                    sheet, state["selected_angle"], state.get("feedback"), previous, review,
                    self._length(state),
                ),
                schema=Script,
            )

        result, report, stats = await self._fact_checked(
            "narration script", write, sheet, state.get("script")
        )
        return {
            "script": result.model_dump(),
            **self._with_fact_check(state, "script", report, stats),
            "feedback": None,
        }

    def gate_script(self, state: ProjectState) -> Command:
        script = Script.model_validate(state["script"])
        decision = ask("script", {
            "script": state["script"],
            "word_count": script.word_count,
            "estimated_seconds": round(script.word_count / 155 * 60, 1),
            "target_seconds": self._length(state).seconds,
            "fact_check": (state.get("fact_checks") or {}).get("script"),
        })
        if decision.action == "revise":
            return Command(goto="script", update={"feedback": decision.feedback})
        update: dict = {"feedback": decision.feedback}
        if texts := decision.edits.get("narration"):
            for segment, text in zip(script.segments, texts, strict=True):
                segment.narration = text
            update["script"] = script.model_dump()
        return Command(goto="audio", update=update)

    # ------------------------------------------------------------------ audio

    async def audio(self, state: ProjectState) -> dict:
        project_id = state["project_id"]
        script = Script.model_validate(state["script"])
        targets = state.get("audio_targets") or ["narration", "bgm"]
        update: dict = {"feedback": None, "audio_targets": None}

        narration = state.get("narration")
        if "narration" in targets or not narration:
            voice_id = state.get("voice_id") or self.settings.elevenlabs_voice_id
            speech = await self.tts.speak(script.full_text, voice_id)
            words, segments, duration = build_timings(
                [s.narration for s in script.segments], speech.characters, speech.starts,
                speech.ends,
            )
            key = f"projects/{project_id}/audio/narration-{uuid.uuid4().hex[:8]}.mp3"
            await self.storage.put(key, speech.audio, "audio/mpeg")
            narration = Narration(
                audio_key=key, voice_id=voice_id, duration=duration, words=words,
                segments=segments,
            ).model_dump()
            update["narration"] = narration

        if "bgm" in targets or not state.get("bgm"):
            seconds = math.ceil(narration["duration"]) + 2
            brief = await self.claude.generate(
                system=prompts.SYSTEM,
                prompt=prompts.music(
                    script.full_text, state["selected_angle"], seconds, state.get("feedback")
                ),
                schema=MusicBrief,
                effort="medium",
            )
            track = (await self.magnific.music(brief.prompt, seconds))[0]
            key = f"projects/{project_id}/audio/bgm-{uuid.uuid4().hex[:8]}.mp3"
            await self.storage.put(key, track, "audio/mpeg")
            update["bgm"] = Bgm(audio_key=key, prompt=brief.prompt, seconds=seconds).model_dump()
        return update

    def gate_audio(self, state: ProjectState) -> Command:
        decision = ask("audio", {"narration": state["narration"], "bgm": state["bgm"]})
        if decision.action == "revise":
            return Command(goto="audio", update={
                "feedback": decision.feedback,
                "audio_targets": decision.edits.get("regenerate", ["narration", "bgm"]),
                "voice_id": decision.edits.get("voice_id", state.get("voice_id")),
            })
        return Command(goto="bible", update={"feedback": decision.feedback})

    # ------------------------------------------------------------------ visuals

    async def bible(self, state: ProjectState) -> dict:
        update: dict = {"feedback": None, "bible_image_only": None}
        bible = state.get("bible")
        style = await self._style_reference(state)
        if not (state.get("bible_image_only") and bible):
            result = await self.claude.generate(
                system=prompts.SYSTEM,
                prompt=prompts.bible(
                    state["fact_sheet"], state["selected_angle"], state["script"],
                    state.get("feedback"), bible, has_style_reference=style is not None,
                ),
                schema=StyleBible,
                images=[style] if style else None,
            )
            bible = result.model_dump()
            update["bible"] = bible

        looks = bible["character"]["looks"]
        sheets = await asyncio.gather(*(
            self._images(
                state,
                prompts.character_sheet_image(bible, look, has_style_reference=style is not None),
                [style] if style else [],
                count=1,
            )
            for look in looks
        ))
        update["character_refs"] = {
            look["id"]: await self._store_image(
                state["project_id"], "bible", f"character-{look['id']}", images[0]
            )
            for look, images in zip(looks, sheets, strict=True)
        }
        return update

    def gate_bible(self, state: ProjectState) -> Command:
        decision = ask(
            "bible", {"bible": state["bible"], "character_refs": state["character_refs"]}
        )
        if decision.action == "revise":
            return Command(goto="bible", update={
                "feedback": decision.feedback,
                "bible_image_only": bool(decision.edits.get("image_only")),
                "style_ref_key": decision.edits.get("style_ref_key", state.get("style_ref_key")),
                **model_edits(decision),
            })
        return Command(goto="scenes", update={
            "critic_rounds": 0, "critic_report": None, "feedback": decision.feedback,
        })

    async def scenes(self, state: ProjectState) -> dict:
        script = state["script"]
        timings = state["narration"]["segments"]
        report = state.get("critic_report")
        result = await self.claude.generate(
            system=prompts.SYSTEM,
            prompt=prompts.scenes(
                script, timings, state["bible"], state["fact_sheet"],
                report if report and not report["passed"] else None,
                state.get("feedback"), state.get("scenes"),
            ),
            schema=SceneSet,
        )
        drafts = sorted(result.scenes, key=lambda s: s.order)
        if len(drafts) < len(timings):
            raise ValueError(f"expected {len(timings)} scenes, got {len(drafts)}")
        looks = {look["id"] for look in state["bible"]["character"]["looks"]}
        scenes = []
        # Extra drafts beyond the segment count are dropped on purpose.
        for order, (draft, timing, segment) in enumerate(
            zip(drafts, timings, script["segments"], strict=False), start=1
        ):
            scenes.append({
                **draft.model_dump(), "order": order,
                "character_look": draft.character_look if draft.character_look in looks else None,
                "narration": segment["narration"], "start": timing["start"], "end": timing["end"],
            })
        return {"scenes": scenes, "feedback": None}

    async def critic(self, state: ProjectState) -> Command:
        report = await self.claude.generate(
            system=prompts.SYSTEM,
            prompt=prompts.critic(
                state["scenes"], state["script"], state["bible"], state["fact_sheet"]
            ),
            schema=CriticReport,
        )
        rounds = state.get("critic_rounds", 0) + 1
        update = {"critic_report": report.model_dump(), "critic_rounds": rounds}
        needs_rewrite = not report.passed and report.issues
        if needs_rewrite and rounds <= self.settings.max_critic_rounds:
            return Command(goto="scenes", update=update)
        return Command(goto="gate_scenes", update=update)

    def gate_scenes(self, state: ProjectState) -> Command:
        decision = ask("scenes", {
            "scenes": state["scenes"],
            "critic_report": state.get("critic_report"),
            "critic_rounds": state.get("critic_rounds", 0),
        })
        if decision.action == "revise":
            return Command(goto="scenes", update={
                "feedback": decision.feedback, "critic_rounds": 0, "critic_report": None,
            })
        scenes = [dict(scene) for scene in state["scenes"]]
        for edit in decision.edits.get("scenes", []):
            for scene in scenes:
                if scene["order"] == edit.get("order"):
                    scene.update({k: v for k, v in edit.items() if k in SCENE_EDIT_FIELDS})
        return Command(goto="keyframes", update={
            "scenes": scenes, "feedback": decision.feedback, **model_edits(decision),
        })

    async def keyframes(self, state: ProjectState) -> dict:
        project_id = state["project_id"]
        existing = {k: list(v) for k, v in (state.get("keyframes") or {}).items()}
        selected = dict(state.get("selected_keyframes") or {})
        targets = set(state.get("regen_orders") or [
            s["order"] for s in state["scenes"] if str(s["order"]) not in existing
        ])
        characters = {
            look: await self.storage.get(key) for look, key in state["character_refs"].items()
        }
        style = await self._style_reference(state)
        limit = asyncio.Semaphore(self.settings.image_concurrency)

        async def generate(scene: dict) -> list[bytes]:
            character = characters.get(scene.get("character_look") or "")
            refs = ([character] if character else []) + ([style] if style else [])
            prompt = prompts.keyframe_image(
                scene, state.get("feedback"), character is not None, style is not None
            )
            async with limit:
                return await self._images(state, prompt, refs, self.settings.keyframe_candidates)

        scenes = [scene for scene in state["scenes"] if scene["order"] in targets]
        results = await asyncio.gather(*(generate(scene) for scene in scenes))

        added: dict[str, list[str]] = {}
        for scene, images in zip(scenes, results, strict=True):
            order = str(scene["order"])
            for data in images:
                key = await self._store_image(project_id, "keyframes", f"scene-{order}", data)
                added.setdefault(order, []).append(key)
        for order, keys in added.items():
            selected[order] = len(existing.get(order, []))
            existing[order] = existing.get(order, []) + keys
        return {
            "keyframes": existing, "selected_keyframes": selected, "regen_orders": None,
            "feedback": None,
        }

    def gate_keyframes(self, state: ProjectState) -> Command:
        decision = ask("keyframes", {
            "scenes": [{k: s[k] for k in ("order", "narration", "image_prompt", "start", "end")}
                       for s in state["scenes"]],
            "keyframes": state["keyframes"],
            "selected": state["selected_keyframes"],
            "image_model": self._image_model(state),
            "image_quality": self._image_quality(state),
        })
        if decision.action == "regenerate":
            return Command(goto="keyframes", update={
                "regen_orders": decision.scene_orders, "feedback": decision.feedback,
                **model_edits(decision),
            })
        selections = {str(k): int(v) for k, v in decision.edits.get("selections", {}).items()}
        return Command(
            goto="preview",
            update={"selected_keyframes": {**state["selected_keyframes"], **selections}},
        )

    # ------------------------------------------------------------------ animatic

    async def preview(self, state: ProjectState) -> dict:
        return {"preview_key": await self._render(state, "preview", "image"),
                "status": "preview_ready"}

    def gate_preview(self, state: ProjectState) -> Command:
        decision = ask("preview", {
            "preview_key": state["preview_key"],
            "caption_style": self._caption_style(state).model_dump(),
        })
        if decision.action == "regenerate":
            return Command(goto="keyframes", update={
                "regen_orders": decision.scene_orders, "feedback": decision.feedback,
            })
        if decision.action == "revise":
            # Caption changes only re-render the animatic; nothing is regenerated.
            return Command(goto="preview", update=self._caption_update(state, decision))
        return Command(goto="motion", update={
            "feedback": decision.feedback, **self._caption_update(state, decision),
        })

    # ------------------------------------------------------------------ video

    async def motion(self, state: ProjectState) -> dict:
        scenes = [{**scene, "clip_seconds": clip_seconds(scene)} for scene in state["scenes"]]
        previous = [
            {"order": s["order"], "video_prompt": s["video_prompt"]}
            for s in state["scenes"] if s.get("video_prompt")
        ]
        plan = await self.claude.generate(
            system=prompts.SYSTEM,
            prompt=prompts.motion(scenes, state["bible"], state.get("feedback"), previous or None),
            schema=MotionPlan,
            effort="medium",
        )
        by_order = {shot.order: shot.video_prompt for shot in plan.shots}
        missing = [scene["order"] for scene in scenes if scene["order"] not in by_order]
        if missing:
            raise ValueError(f"motion plan is missing scenes {missing}")
        return {
            "scenes": [{**scene, "video_prompt": by_order[scene["order"]]} for scene in scenes],
            "feedback": None,
        }

    def gate_motion(self, state: ProjectState) -> Command:
        shots = [{k: scene.get(k) for k in SHOT_FIELDS} for scene in state["scenes"]]
        candidates = self.settings.clip_candidates
        decision = ask("motion", {
            "shots": shots,
            "estimate": {
                "model": self._video_model(state),
                "clips": len(shots) * candidates,
                "total_seconds": sum(shot["clip_seconds"] for shot in shots) * candidates,
            },
        })
        if decision.action == "revise":
            return Command(goto="motion", update={"feedback": decision.feedback})
        scenes = [dict(scene) for scene in state["scenes"]]
        for edit in decision.edits.get("shots", []):
            for scene in scenes:
                if scene["order"] == edit.get("order"):
                    scene.update({k: v for k, v in edit.items() if k in MOTION_EDIT_FIELDS})
        return Command(goto="clips", update={
            "scenes": scenes, "feedback": decision.feedback, **model_edits(decision),
        })

    async def clips(self, state: ProjectState) -> dict:
        project_id = state["project_id"]
        existing = {k: list(v) for k, v in (state.get("clips") or {}).items()}
        selected = dict(state.get("selected_clips") or {})
        targets = set(state.get("regen_clip_orders") or [
            s["order"] for s in state["scenes"] if str(s["order"]) not in existing
        ])
        video_model = self._video_model(state)
        limit = asyncio.Semaphore(self.settings.video_concurrency)

        async def generate(scene: dict) -> list[bytes]:
            order = str(scene["order"])
            keyframe = state["keyframes"][order][state["selected_keyframes"][order]]
            image = await self.storage.get(keyframe)
            _, content_type = image_type(image) or ("jpg", "image/jpeg")
            prompt = prompts.clip_prompt(scene, state.get("feedback"))
            async with limit:
                batches = await asyncio.gather(*(
                    self.magnific.image_to_video(
                        video_model, image, content_type, prompt,
                        scene["clip_seconds"], self.settings.video_negative_prompt,
                    )
                    for _ in range(self.settings.clip_candidates)
                ))
            return [video for batch in batches for video in batch]

        scenes = [scene for scene in state["scenes"] if scene["order"] in targets]
        # One failed clip must not throw away the clips that were already paid for.
        results = await asyncio.gather(*(generate(s) for s in scenes), return_exceptions=True)

        errors = {
            order: error for order, error in (state.get("clip_errors") or {}).items()
            if int(order) not in targets
        }
        for scene, result in zip(scenes, results, strict=True):
            order = str(scene["order"])
            if isinstance(result, BaseException):
                errors[order] = f"{type(result).__name__}: {result}"
                continue
            keys = []
            for data in result:
                key = f"projects/{project_id}/clips/scene-{order}-{uuid.uuid4().hex[:8]}.mp4"
                await self.storage.put(key, data, "video/mp4")
                keys.append(key)
            selected[order] = len(existing.get(order, []))
            existing[order] = existing.get(order, []) + keys
        return {
            "clips": existing, "selected_clips": selected, "clip_errors": errors,
            "regen_clip_orders": None, "feedback": None,
        }

    def gate_clips(self, state: ProjectState) -> Command:
        decision = ask("clips", {
            "shots": [{k: scene.get(k) for k in SHOT_FIELDS} for scene in state["scenes"]],
            "clips": state.get("clips") or {},
            "selected": state.get("selected_clips") or {},
            "errors": state.get("clip_errors") or {},
            "video_model": self._video_model(state),
        })
        if decision.action == "regenerate":
            return Command(goto="clips", update={
                "regen_clip_orders": decision.scene_orders, "feedback": decision.feedback,
                **model_edits(decision),
            })
        selections = {str(k): int(v) for k, v in decision.edits.get("selections", {}).items()}
        return Command(
            goto="final", update={"selected_clips": {**state["selected_clips"], **selections}}
        )

    # ------------------------------------------------------------------ output

    async def final(self, state: ProjectState) -> dict:
        return {"final_key": await self._render(state, "final", "video"), "status": "final_ready"}

    def gate_final(self, state: ProjectState) -> Command:
        decision = ask("final", {
            "final_key": state["final_key"],
            "caption_style": self._caption_style(state).model_dump(),
        })
        if decision.action == "revise":
            # Caption changes re-cut the final from the approved clips; nothing is regenerated.
            return Command(goto="final", update=self._caption_update(state, decision))
        return Command(goto=END, update={"status": "done"})
