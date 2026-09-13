"""Turn ElevenLabs character alignment into word and scene timings."""

from app.domain.models import SegmentTiming, WordTiming

TAIL_SECONDS = 0.6


def build_timings(
    segments: list[str],
    characters: list[str],
    starts: list[float],
    ends: list[float],
    tail: float = TAIL_SECONDS,
) -> tuple[list[WordTiming], list[SegmentTiming], float]:
    """Map narration segments onto the spoken audio.

    The TTS input is the segments joined by single spaces. When the alignment has one
    entry per input character we index it directly; otherwise we scale indices
    proportionally, which stays monotonic and close enough for scene cuts.
    """
    if not characters:
        raise ValueError("alignment is empty")

    parts = [s.strip() for s in segments]
    text = " ".join(parts)
    scale = 1.0 if len(characters) == len(text) else len(characters) / len(text)

    def at(index: int) -> int:
        return min(int(index * scale), len(characters) - 1)

    words: list[WordTiming] = []
    index = 0
    for word in text.split(" "):
        if word:
            first, last = at(index), at(index + len(word) - 1)
            words.append(WordTiming(text=word, start=starts[first], end=ends[last]))
        index += len(word) + 1

    duration = round(ends[-1] + tail, 3)
    offsets, index = [], 0
    for part in parts:
        offsets.append(index)
        index += len(part) + 1

    timings: list[SegmentTiming] = []
    for i, offset in enumerate(offsets):
        start = 0.0 if i == 0 else starts[at(offset)]
        end = duration if i == len(offsets) - 1 else starts[at(offsets[i + 1])]
        timings.append(SegmentTiming(order=i + 1, start=round(start, 3), end=round(end, 3)))
    return words, timings, duration
