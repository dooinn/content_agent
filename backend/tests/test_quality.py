"""Metrics read back from a real graph run with fake providers."""

from datetime import UTC, datetime

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from test_pipeline import SEGMENTS, FakeClaude, FakeMagnific, FakeRenderer, FakeTTS, step

from app import usage
from app.config import Settings
from app.graph.builder import build_graph
from app.graph.state import Deps
from app.pricing import llm_cost
from app.quality import project_metrics, summarize
from app.runtime import ProjectRecord


class MeteredClaude(FakeClaude):
    async def research(self, *, system, prompt):
        usage.record("llm", provider="anthropic", model="claude-sonnet-5", purpose="research",
                     input_tokens=20_000, output_tokens=2_000, web_searches=5)
        return await super().research(system=system, prompt=prompt)

    async def generate(self, *, system, prompt, schema, effort="high", images=None):
        usage.record("llm", provider="anthropic", model="claude-sonnet-5",
                     purpose=schema.__name__, input_tokens=1_000, output_tokens=500)
        return await super().generate(system=system, prompt=prompt, schema=schema,
                                      effort=effort, images=images)


class MeteredMagnific(FakeMagnific):
    async def gpt_image(self, prompt, reference_images=None, count=1, quality="high"):
        images = await super().gpt_image(prompt, reference_images, count, quality)
        usage.record("media", provider="magnific", model="gpt-image-2", unit="images",
                     units=len(images))
        return images


DECISIONS = [
    {"action": "approve"},                                     # research
    {"action": "revise", "feedback": "darker"},                # angle
    {"action": "select", "choice": 0},                         # angle
    {"action": "approve"},                                     # script
    {"action": "approve"},                                     # audio
    {"action": "approve"},                                     # bible
    {"action": "approve"},                                     # scenes
    {"action": "regenerate", "scene_orders": [2]},             # keyframes
    {"action": "approve"},                                     # keyframes
    {"action": "approve"},                                     # preview
    {"action": "approve"},                                     # motion
    {"action": "regenerate", "scene_orders": [4]},             # clips (scene 4 failed)
    {"action": "approve"},                                     # clips
    {"action": "approve"},                                     # final
]  # fmt: skip


def metered_graph(storage_dir):
    from app.services.storage import LocalStorage

    deps = Deps(
        settings=Settings(_env_file=None, elevenlabs_voice_id="voice", keyframe_candidates=2,
                          max_critic_rounds=2, max_fact_rewrites=2, video_model="kling-v3-pro"),
        claude=MeteredClaude(), magnific=MeteredMagnific(), tts=FakeTTS(),
        storage=LocalStorage(storage_dir), renderer=FakeRenderer(),
    )
    return build_graph(deps, InMemorySaver()), deps


async def run_metered_project(graph, thread="q1"):
    _, pending = await step(graph, {"project_id": thread, "topic": "Napoleon"}, thread=thread)
    for decision in DECISIONS:
        assert pending is not None
        _, pending = await step(graph, Command(resume=decision), thread=thread)
    assert pending is None


@pytest.fixture
def metered(tmp_path):
    return metered_graph(tmp_path)


async def test_metrics_from_a_full_run(metered):
    graph, _ = metered
    await run_metered_project(graph)

    now = datetime.now(UTC)
    record = ProjectRecord(id="q1", topic="Napoleon", status="done", created_at=now,
                           updated_at=now)
    metrics = await project_metrics(graph, record)

    reviews = metrics["reviews"]
    assert reviews["decisions"] == len(DECISIONS)
    assert reviews["rework"] == 3 and reviews["with_feedback"] == 1
    assert reviews["by_stage"]["angle"] == {
        "decisions": 2, "first_try": False, "actions": {"revise": 1, "select": 1},
    }
    assert reviews["by_stage"]["script"]["first_try"]
    assert not reviews["by_stage"]["clips"]["first_try"]
    assert reviews["first_try_rate"] == pytest.approx(8 / 11)

    # The first angle draft invented a claim; the rewrite and the later revision were clean.
    angles = metrics["fact_check"]["angles"]
    assert angles == {"runs": 2, "drafts": 3, "first_draft_issues": 1,
                      "clean_first_drafts": 1, "final_passed": True}
    assert metrics["fact_check"]["script"]["drafts"] == 1

    critic = metrics["critic"]
    assert critic["reports"] == 2 and critic["issues_found"] == 1
    assert critic["categories"] == {"anachronism": 1} and critic["final_passed"]

    media = metrics["media"]
    n = len(SEGMENTS)
    assert media["character_sheets"] == 2 and media["keyframes"] == n * 2 + 2
    assert media["clips"] == (n - 1) + 1  # scene 4 failed once, then regenerated
    assert media["narration_takes"] == 1 and media["music_tracks"] == 1

    llm = metrics["llm"]
    generate_calls = llm["calls"] - 1
    expected = llm_cost({"model": "claude-sonnet-5", "input_tokens": 20_000,
                         "output_tokens": 2_000, "web_searches": 5})
    expected += generate_calls * llm_cost({"model": "claude-sonnet-5", "input_tokens": 1_000,
                                           "output_tokens": 500})
    assert llm["cost_usd"] == pytest.approx(expected, abs=1e-4)
    assert llm["web_searches"] == 5 and llm["unpriced_calls"] == 0
    assert set(llm["cost_by_node"]) >= {"research", "angles", "script", "scenes", "critic"}

    # Media usage recorded inside asyncio.gather still reaches the state channel.
    state = (await graph.aget_state({"configurable": {"thread_id": "q1"}})).values
    images = sum(e["units"] for e in state["usage"] if e.get("unit") == "images")
    assert images == media["images"]

    summary = summarize([metrics])
    assert summary["projects"] == 1 and summary["finished"] == 1
    assert summary["fact_check"]["clean_first_draft_rate"] == pytest.approx(
        (1 + 1) / 3  # angles: 1 of 2 runs clean; script: 1 of 1
    )
    assert summary["critic"]["categories"] == {"anachronism": 1}
    angle_stage = next(s for s in summary["stages"] if s["stage"] == "angle")
    assert angle_stage["first_try_rate"] == 0 and angle_stage["rework_per_project"] == 1


def test_unknown_models_are_not_priced():
    assert llm_cost({"model": "someone-else", "input_tokens": 10}) is None
    one_million_out = llm_cost({"model": "claude-sonnet-5", "output_tokens": 1_000_000})
    assert one_million_out == pytest.approx(10.0)
