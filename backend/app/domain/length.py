"""Video lengths the producer can choose, and the story shape each one needs.

Narration is read at about 155 words per minute, and every narration segment becomes one scene
(one keyframe set, one video clip), so the length drives both the script and the generation cost.
"""

from dataclasses import dataclass
from typing import Literal, get_args

TargetSeconds = Literal[30, 60, 120, 180]
TARGET_SECONDS: tuple[int, ...] = get_args(TargetSeconds)
DEFAULT_TARGET_SECONDS = 30
WORDS_PER_MINUTE = 155


@dataclass(frozen=True)
class LengthProfile:
    seconds: int
    words: tuple[int, int]
    segments: tuple[int, int]
    segment_words: tuple[int, int]
    facts: tuple[int, int]
    structure: str

    @property
    def label(self) -> str:
        """Short UI label: '30 sec', '2 min'."""
        return f"{self.seconds} sec" if self.seconds < 60 else f"{self.seconds // 60} min"

    @property
    def adjective(self) -> str:
        """For prompts: 'a 30-second video', 'a 2-minute video'."""
        if self.seconds < 60:
            return f"{self.seconds}-second"
        return f"{self.seconds // 60}-minute"

    @property
    def scene_seconds(self) -> tuple[int, int]:
        low, high = (words / WORDS_PER_MINUTE * 60 for words in self.segment_words)
        return max(3, round(low)), round(high)


PROFILES: dict[int, LengthProfile] = {
    profile.seconds: profile
    for profile in [
        LengthProfile(
            30, words=(70, 80), segments=(5, 7), segment_words=(8, 16), facts=(8, 12),
            structure="One story with one emotional turn, not a mini-biography.",
        ),
        LengthProfile(
            60, words=(140, 155), segments=(8, 10), segment_words=(12, 20), facts=(10, 15),
            structure="One story with a clear turn, room for one or two vivid supporting "
            "details, and a payoff. Not a mini-biography.",
        ),
        LengthProfile(
            120, words=(280, 310), segments=(14, 18), segment_words=(14, 22), facts=(14, 20),
            structure="One story in three acts with two or three turns and rising stakes. It may "
            "span years of the figure's life but keeps a single throughline; it is not a "
            "biography.",
        ),
        LengthProfile(
            180, words=(420, 465), segments=(20, 26), segment_words=(14, 24), facts=(18, 25),
            structure="One story in three acts with several turns, rising stakes, and a midpoint "
            "reversal. It may span years of the figure's life but keeps a single throughline; "
            "it is not a biography.",
        ),
    ]
}


def length_profile(seconds: int | None) -> LengthProfile:
    return PROFILES.get(seconds or DEFAULT_TARGET_SECONDS, PROFILES[DEFAULT_TARGET_SECONDS])
