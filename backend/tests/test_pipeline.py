"""End-to-end graph flow with fake services: every gate, fact checks, the critic loop,
character looks, model choices, caption re-renders, and regeneration."""

import math
from datetime import date
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.config import Settings
from app.domain.models import (
    AngleOptions,
    CaptionStyle,
    CharacterLook,
    CharacterSpec,
    CriticIssue,
    CriticReport,
    Fact,
    FactCheckIssue,
    FactCheckReport,
    FactSheet,
    GateDecision,
    MotionPlan,
    MotionShot,
    MusicBrief,
    SceneDraft,
    SceneSet,
    Script,
    ScriptSegment,
    Source,
    StoryAngle,
    StyleBible,
)
from app.graph.builder import build_graph
from app.graph.pipeline import check_eligibility, enforce_source_rules, validate_decision
from app.graph.state import Deps
from app.llm.claude import ResearchResult
from app.services.elevenlabs import SpeechResult
from app.services.magnific import MagnificError
from app.services.storage import LocalStorage

PNG = b"\x89PNG\r\n\x1a\nfake"
SEGMENTS = [
    ("hook", "Napoleon once lost a battle to rabbits."),
    ("setup", "In 1807 he ordered a celebratory hunt."),
    ("twist", "Hundreds of tame rabbits charged the Emperor instead of fleeing."),
    ("payoff", "His men retreated to the carriages under furry assault."),
    ("closer", "Europe could not stop him. Bunnies could."),
]
# Scene 4 names a look the bible does not define, so it must fall back to no character.
SCENE_LOOKS = {1: "young", 2: None, 3: "young", 4: "unknown", 5: "mature"}


def fact_sheet(death_year: int = 1821) -> FactSheet:
    return FactSheet(
        figure="Napoleon Bonaparte", born="1769", died=str(death_year), death_year=death_year,
        era="Napoleonic era", region="France", summary="Emperor of the French.",
        appearance_notes="Average height, grey eyes.", costume_notes="Chasseur uniform.",
        setting_notes="Tilsit, 1807.",
        facts=[
            Fact(id="F1", claim="The rabbit hunt story", status="disputed", source_ids=["S1"]),
            Fact(id="F2", claim="Born in Corsica", status="verified", source_ids=["S1"]),
            Fact(id="F3", claim="Liked rabbits", status="verified", source_ids=["S2"]),
        ],
        sources=[
            Source(id="S1", title="Britannica", url="https://example.com/b", tier="reference"),
            Source(id="S2", title="Listicle", url="https://example.com/l", tier="popular"),
        ],
    )


class FakeClaude:
    def __init__(self, death_year: int = 1821):
        self.death_year = death_year
        self.calls: list[str] = []
        self.prompts: dict[str, list[str]] = {}
        self.images_seen: dict[str, int] = {}
        self.critic_calls = 0
        self.fact_checks = 0

    async def research(self, *, system, prompt):
        self.calls.append("research")
        return ResearchResult(notes="notes", sources=[{"id": "S1", "title": "S", "url": "u"}])

    async def generate(self, *, system, prompt, schema, effort="high", images=None):
        name = schema.__name__
        self.calls.append(name)
        self.prompts.setdefault(name, []).append(prompt)
        self.images_seen[name] = len(images or [])
        if schema is FactSheet:
            return fact_sheet(self.death_year)
        if schema is FactCheckReport:
            self.fact_checks += 1
            if self.fact_checks == 1:  # the first angle draft invents an age
                issue = FactCheckIssue(location="angle 1 hook_line", claim="at fifteen",
                                       problem="not_in_fact_sheet", suggested_fix="drop the age")
                return FactCheckReport(passed=False, issues=[issue])
            return FactCheckReport(passed=True, issues=[])
        if schema is AngleOptions:
            angle = StoryAngle(title="Rabbits", hook_line="He lost to rabbits.", logline="...",
                               fact_ids=["F1"], why_it_works="irony", accuracy_notes="disputed")
            return AngleOptions(angles=[angle, angle.model_copy(update={"title": "Other"})])
        if schema is Script:
            return Script(title="Rabbits", segments=[
                ScriptSegment(beat=b, narration=t, fact_ids=["F1"]) for b, t in SEGMENTS
            ])
        if schema is MusicBrief:
            return MusicBrief(prompt="playful baroque strings")
        if schema is StyleBible:
            def look(look_id: str, age: str) -> CharacterLook:
                return CharacterLook(id=look_id, label=look_id, age=age, physical_description="...",
                                     costume="uniform", sheet_prompt=f"{look_id} portrait")
            return StyleBible(
                visual_style="painterly", color_palette="warm", lighting="golden hour",
                period_details=["bicorne"], anachronisms_to_avoid=["zippers"],
                character=CharacterSpec(name="Napoleon", signature_props=["bicorne"],
                                        looks=[look("young", "24"), look("mature", "50")]),
            )
        if schema is SceneSet:
            return SceneSet(scenes=[
                SceneDraft(order=i, description="d", shot_type="wide", camera_move="push-in",
                           character_look=SCENE_LOOKS[i], image_prompt=f"scene {i}")
                for i in range(1, len(SEGMENTS) + 1)
            ])
        if schema is MotionPlan:
            return MotionPlan(shots=[
                MotionShot(order=i, video_prompt=f"motion {i}")
                for i in range(1, len(SEGMENTS) + 1)
            ])
        if schema is CriticReport:
            self.critic_calls += 1
            if self.critic_calls == 1:
                issue = CriticIssue(scene_order=2, category="anachronism", detail="zipper",
                                    suggested_fix="use buttons")
                return CriticReport(passed=False, issues=[issue])
            return CriticReport(passed=True, issues=[])
        raise AssertionError(schema)


class FakeMagnific:
    def __init__(self):
        self.image_calls: list[tuple[int, int, str]] = []  # (reference count, images, prompt)
        self.image_qualities: list[str] = []
        self.video_calls: list[tuple[str, int, str]] = []  # (prompt, seconds, model)
        self.failed_scene_four = False

    async def gpt_image(self, prompt, reference_images=None, count=1, quality="high"):
        self.image_calls.append((len(reference_images or []), count, prompt))
        self.image_qualities.append(quality)
        return [PNG] * count

    async def image_to_video(self, model, image, content_type, prompt, seconds,
                             negative_prompt=""):
        assert image == PNG and content_type == "image/png"
        self.video_calls.append((prompt, seconds, model))
        if prompt.startswith("motion 4") and not self.failed_scene_four:
            self.failed_scene_four = True
            raise MagnificError("task failed")
        return [b"mp4clip"]

    async def music(self, prompt, seconds):
        return [b"ID3music"]


class FakeTTS:
    async def speak(self, text, voice_id):
        n = len(text)
        return SpeechResult(audio=b"ID3voice", characters=list(text),
                            starts=[i * 0.07 for i in range(n)],
                            ends=[(i + 1) * 0.07 for i in range(n)])


class FakeRenderer:
    def __init__(self):
        self.renders: list[tuple[list, str, CaptionStyle | None]] = []  # (clips, output, style)

    async def render(self, workdir: Path, clips, narration, bgm, words, total,
                     output="preview.mp4", caption_style=None):
        self.renders.append((clips, output, caption_style))
        assert (workdir / narration).exists() and (workdir / bgm).exists()
        assert all((workdir / clip.path).exists() for clip in clips)
        path = workdir / output
        path.write_bytes(b"mp4")
        return path


@pytest.fixture
def setup(tmp_path):
    def make(death_year: int = 1821):
        deps = Deps(
            settings=Settings(_env_file=None, elevenlabs_voice_id="voice", keyframe_candidates=2,
                              max_critic_rounds=2, max_fact_rewrites=2,
                              video_model="kling-v3-pro"),
            claude=FakeClaude(death_year), magnific=FakeMagnific(), tts=FakeTTS(),
            storage=LocalStorage(tmp_path), renderer=FakeRenderer(),
        )
        return build_graph(deps, InMemorySaver()), deps
    return make


async def step(graph, graph_input, thread="p1"):
    config = {"configurable": {"thread_id": thread}}
    await graph.ainvoke(graph_input, config)
    snap = await graph.aget_state(config)
    return snap, (snap.interrupts[0].value if snap.interrupts else None)


def keyframe_call(calls, prompt_ending: str):
    return next(call for call in calls if call[2].endswith(prompt_ending))


async def test_full_flow_through_every_gate(setup):
    graph, deps = setup()
    claude, magnific, renderer = deps.claude, deps.magnific, deps.renderer
    await deps.storage.put("uploads/style.png", PNG, "image/png")
    snap, pending = await step(graph, {
        "project_id": "p1", "topic": "Napoleon", "style_ref_key": "uploads/style.png",
        "image_quality": "medium",
    })
    assert pending["stage"] == "research" and pending["payload"]["eligibility"]["ok"]
    statuses = {f["id"]: f["status"] for f in pending["payload"]["fact_sheet"]["facts"]}
    assert statuses == {"F1": "disputed", "F2": "verified", "F3": "disputed"}

    # Feedback on an approval steers the next stage; the length can change before the story.
    decision = {"action": "approve", "feedback": "Focus on the hunt",
                "edits": {"target_seconds": 60}}
    snap, pending = await step(graph, Command(resume=decision))
    assert pending["stage"] == "angle" and len(pending["payload"]["angles"]) == 2
    first_angles, rewrite = claude.prompts["AngleOptions"]
    assert "<producer_direction>\nFocus on the hunt" in first_angles
    assert "previous_draft" not in first_angles
    assert "fact checker flagged" in rewrite and "at fifteen" in rewrite
    assert pending["payload"]["fact_check"]["passed"]

    snap, pending = await step(graph, Command(resume={"action": "select", "choice": 1}))
    assert snap.values["selected_angle"]["title"] == "Other"
    assert pending["stage"] == "script" and pending["payload"]["fact_check"]["passed"]
    assert "producer_direction" not in claude.prompts["Script"][0]
    script_prompt = claude.prompts["Script"][0]
    assert "1-minute" in script_prompt and "140 to 155 words" in script_prompt
    assert "fill 1 min" in claude.prompts["AngleOptions"][0]
    assert pending["payload"]["target_seconds"] == 60
    script = Script.model_validate(snap.values["script"])
    assert pending["payload"]["word_count"] == script.word_count

    snap, pending = await step(graph, Command(resume={"action": "approve"}))
    assert pending["stage"] == "audio"
    narration = snap.values["narration"]
    assert len(narration["segments"]) == len(SEGMENTS)
    assert snap.values["bgm"]["seconds"] >= int(narration["duration"]) + 2

    snap, pending = await step(graph, Command(resume={"action": "approve"}))
    assert pending["stage"] == "bible"
    refs = snap.values["character_refs"]
    assert set(refs) == {"young", "mature"}
    assert all([await deps.storage.exists(key) for key in refs.values()])
    assert claude.images_seen["StyleBible"] == 1  # Claude sees the style reference
    sheet_calls = magnific.image_calls[:2]
    assert all(n_refs == 1 and "style reference" in prompt for n_refs, _, prompt in sheet_calls)

    snap, pending = await step(graph, Command(resume={"action": "approve"}))
    assert pending["stage"] == "scenes"
    assert claude.critic_calls == 2 and claude.calls.count("SceneSet") == 2
    assert pending["payload"]["critic_report"]["passed"]
    assert [s["character_look"] for s in snap.values["scenes"]] == [
        "young", None, "young", None, "mature",
    ]

    edit = {"scenes": [{"order": 1, "image_prompt": "edited", "narration": "ignored"}]}
    decision = {"action": "approve", "edits": edit, "feedback": "moody light"}
    snap, pending = await step(graph, Command(resume=decision))
    assert pending["stage"] == "keyframes"
    assert pending["payload"]["image_quality"] == "medium"
    assert snap.values["scenes"][0]["image_prompt"] == "edited"
    assert snap.values["scenes"][0]["narration"] == SEGMENTS[0][1]
    assert all(len(v) == 2 for v in snap.values["keyframes"].values())
    keyframe_calls = magnific.image_calls[2:]
    assert len(keyframe_calls) == len(SEGMENTS)
    assert set(magnific.image_qualities) == {"medium"}  # the project's quality, not the default
    # Character scenes send the matching look plus the style image; others send style only.
    for ending, expected_refs in [("edited", 2), ("scene 2", 1), ("scene 4", 1), ("scene 5", 2)]:
        note = f"{ending}\nProducer note: moody light"
        n_refs, count, _ = keyframe_call(keyframe_calls, note)
        assert (n_refs, count) == (expected_refs, 2), ending

    decision = {"action": "regenerate", "scene_orders": [2], "feedback": "darker",
                "edits": {"image_quality": "high"}}
    snap, pending = await step(graph, Command(resume=decision))
    assert pending["stage"] == "keyframes"
    assert len(snap.values["keyframes"]["2"]) == 4 and snap.values["selected_keyframes"]["2"] == 2
    assert magnific.image_qualities[-1] == "high"

    decision = {"action": "approve", "edits": {"selections": {"3": 1}}}
    snap, pending = await step(graph, Command(resume=decision))
    assert pending["stage"] == "preview"
    assert pending["payload"]["caption_style"] == CaptionStyle().model_dump()
    assert await deps.storage.exists(snap.values["preview_key"])
    animatic, output, style = renderer.renders[0]
    assert output == "preview.mp4" and style == CaptionStyle() and len(animatic) == len(SEGMENTS)
    assert animatic[2].path == "scene_03.png" and animatic[2].kind == "image"

    # Caption changes only re-render the animatic; no image is generated.
    images_before = len(magnific.image_calls)
    decision = {"action": "revise", "edits": {"caption_style": {"font": "cinzel", "size": 100}}}
    snap, pending = await step(graph, Command(resume=decision))
    assert pending["stage"] == "preview" and len(renderer.renders) == 2
    assert renderer.renders[-1][2] == CaptionStyle(font="cinzel", size=100)
    assert len(magnific.image_calls) == images_before

    # Animatic approved with direction for the motion writer.
    decision = {"action": "approve", "feedback": "gentle motion"}
    snap, pending = await step(graph, Command(resume=decision))
    assert pending["stage"] == "motion"
    assert "<producer_direction>\ngentle motion" in claude.prompts["MotionPlan"][0]
    expected = [max(3, min(15, math.ceil(s["end"] - s["start"] - 1e-6)))
                for s in snap.values["scenes"]]
    shots = pending["payload"]["shots"]
    assert [shot["clip_seconds"] for shot in shots] == expected
    assert shots[1]["video_prompt"] == "motion 2"
    assert pending["payload"]["estimate"] == {
        "model": "kling-v3-pro", "clips": len(SEGMENTS), "total_seconds": sum(expected),
    }

    # The reviewer switches the video model right before paying for clips.
    edit = {"shots": [{"order": 1, "video_prompt": "custom motion", "clip_seconds": 6,
                       "narration": "ignored"}], "video_model": "kling-v3-turbo"}
    snap, pending = await step(graph, Command(resume={"action": "approve", "edits": edit}))
    assert pending["stage"] == "clips" and pending["payload"]["video_model"] == "kling-v3-turbo"
    assert ("custom motion", 6, "kling-v3-turbo") in magnific.video_calls
    assert {model for _, _, model in magnific.video_calls} == {"kling-v3-turbo"}
    # Scene 4 failed; the other clips were kept and the reviewer sees the error.
    assert set(snap.values["clips"]) == {"1", "2", "3", "5"}
    assert set(pending["payload"]["errors"]) == {"4"}
    error = validate_decision("clips", GateDecision(action="approve"), snap.values)
    assert "missing scenes [4]" in error

    decision = {"action": "regenerate", "scene_orders": [2, 4]}
    snap, pending = await step(graph, Command(resume=decision))
    assert pending["stage"] == "clips" and pending["payload"]["errors"] == {}
    assert len(snap.values["clips"]["2"]) == 2 and snap.values["selected_clips"]["2"] == 1
    assert len(snap.values["clips"]["4"]) == 1 and len(snap.values["clips"]["1"]) == 1

    decision = {"action": "approve", "edits": {"selections": {"2": 0}}}
    snap, pending = await step(graph, Command(resume=decision))
    assert pending["stage"] == "final" and snap.values["status"] == "final_ready"
    assert await deps.storage.exists(snap.values["final_key"])
    final_cut, output, style = renderer.renders[-1]
    assert output == "final.mp4" and style == CaptionStyle(font="cinzel", size=100)
    assert all(clip.kind == "video" and clip.path.endswith(".mp4") for clip in final_cut)
    assert snap.values["selected_clips"]["2"] == 0

    # A caption tweak on the final re-cuts from the approved clips.
    videos_before = len(magnific.video_calls)
    decision = {"action": "revise", "edits": {"caption_style": {"uppercase": True}}}
    snap, pending = await step(graph, Command(resume=decision))
    assert pending["stage"] == "final" and renderer.renders[-1][1] == "final.mp4"
    assert renderer.renders[-1][2] == CaptionStyle(font="cinzel", size=100, uppercase=True)
    assert len(magnific.video_calls) == videos_before

    snap, pending = await step(graph, Command(resume={"action": "approve"}))
    assert pending is None and snap.values["status"] == "done"


async def test_recent_figures_are_rejected(setup):
    graph, _ = setup(death_year=2010)
    _, pending = await step(graph, {"project_id": "p2", "topic": "Someone"}, thread="p2")
    assert not pending["payload"]["eligibility"]["ok"]
    snap, pending = await step(graph, Command(resume={"action": "approve"}), thread="p2")
    assert pending is None and snap.values["status"] == "rejected"


def test_eligibility_boundary():
    today = date(2026, 1, 1)
    assert check_eligibility(fact_sheet(1951), 75, today)["ok"]
    assert not check_eligibility(fact_sheet(1952), 75, today)["ok"]


def test_popular_only_facts_cannot_be_verified():
    sheet = enforce_source_rules(fact_sheet())
    facts = {fact.id: fact for fact in sheet.facts}
    assert facts["F2"].status == "verified"
    assert facts["F3"].status == "disputed" and "Downgraded" in facts["F3"].note


def test_validate_decision():
    state = {"angles": [{}, {}], "script": {"segments": [{}, {}]},
             "keyframes": {"1": ["a", "b"]}}
    ok = GateDecision(action="select", choice=1)
    assert validate_decision("angle", ok, state) is None
    assert "index" in validate_decision("angle", GateDecision(action="select", choice=5), state)
    assert "not valid" in validate_decision("angle", GateDecision(action="approve"), state)
    bad_edit = GateDecision(action="approve", edits={"narration": ["only one"]})
    assert "one string per segment" in validate_decision("script", bad_edit, state)
    assert "scene_orders" in validate_decision("keyframes", GateDecision(action="regenerate"),
                                               state)
    out_of_range = GateDecision(action="approve", edits={"selections": {"1": 2}})
    assert "out of range" in validate_decision("keyframes", out_of_range, state)
    too_long = GateDecision(action="approve", edits={"shots": [{"order": 1, "clip_seconds": 20}]})
    assert "3 to 15" in validate_decision("motion", too_long, state)
    assert "scene_orders" in validate_decision("clips", GateDecision(action="regenerate"), state)
    unknown_model = GateDecision(action="approve", edits={"video_model": "sora"})
    assert "video_model" in validate_decision("motion", unknown_model, state)
    huge_caption = GateDecision(action="revise", edits={"caption_style": {"size": 400}})
    assert "caption_style" in validate_decision("preview", huge_caption, state)
    assert validate_decision("final", GateDecision(action="approve"), state) is None
