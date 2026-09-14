from app.domain.length import PROFILES, WORDS_PER_MINUTE, length_profile
from app.domain.models import GateDecision
from app.graph.pipeline import validate_decision
from app.llm import prompts

SHEET = {"figure": "Napoleon Bonaparte"}


def test_unknown_lengths_fall_back_to_thirty_seconds():
    assert length_profile(None).seconds == 30
    assert length_profile(45).seconds == 30
    assert length_profile(120).label == "2 min"


def test_profiles_fit_reading_speed_and_one_clip_per_scene():
    for profile in PROFILES.values():
        spoken = sum(profile.words) / 2 / WORDS_PER_MINUTE * 60
        assert abs(spoken - profile.seconds) <= profile.seconds * 0.1, profile.seconds
        # The segment range must be able to hold the word budget.
        assert profile.segments[0] * profile.segment_words[0] <= profile.words[0]
        assert profile.segments[1] * profile.segment_words[1] >= profile.words[1]
        # Kling clips top out at 15 seconds, and every scene is one clip.
        assert profile.scene_seconds[1] <= 15


def test_prompts_scale_with_length():
    short = prompts.script(SHEET, {"title": "t"}, None, None)
    assert "30-second" in short and "70 to 80 words" in short and "span two segments" in short

    long = prompts.script(SHEET, {"title": "t"}, None, None, length=length_profile(180))
    assert "3-minute" in long and "420 to 465 words" in long and "20 to 26 segments" in long
    assert "three acts" in long and "never repeat" in long

    assert "18 to 25 surprising" in prompts.research("Napoleon", None, length_profile(180))
    assert "fill 1 min" in prompts.angles(SHEET, None, None, length=length_profile(60))


def test_length_can_only_change_at_research():
    change = GateDecision(action="approve", edits={"target_seconds": 120})
    assert validate_decision("research", change, {}) is None
    bad = GateDecision(action="approve", edits={"target_seconds": 45})
    assert "one of" in validate_decision("research", bad, {})
    assert "research stage" in validate_decision("audio", change, {})
