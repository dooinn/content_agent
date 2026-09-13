import pytest

from app.services.timing import build_timings


def alignment(text: str, step: float = 0.05):
    indices = range(len(text))
    return list(text), [i * step for i in indices], [(i + 1) * step for i in indices]


def test_segments_are_contiguous_and_cover_the_audio():
    segments = ["Napoleon was not short.", "British cartoons made him tiny."]
    chars, starts, ends = alignment(" ".join(segments))

    words, timings, duration = build_timings(segments, chars, starts, ends, tail=0.5)

    assert duration == round(ends[-1] + 0.5, 3)
    assert timings[0].start == 0.0
    assert timings[0].end == timings[1].start == pytest.approx(starts[len(segments[0]) + 1])
    assert timings[-1].end == duration
    assert [w.text for w in words] == " ".join(segments).split()
    assert words[1].start == pytest.approx(starts[9])  # "was"
    assert words[1].end == pytest.approx(ends[11])


def test_mismatched_alignment_still_produces_ordered_timings():
    segments = ["One two three.", "Four five six.", "Seven eight."]
    text = " ".join(segments)
    chars, starts, ends = alignment(text + "  extra")  # longer than the input text

    words, timings, _ = build_timings(segments, chars, starts, ends)

    assert len(words) == 8
    assert all(a.start <= b.start for a, b in zip(words, words[1:], strict=False))
    assert all(t.start < t.end for t in timings)
    assert [t.order for t in timings] == [1, 2, 3]


def test_empty_alignment_is_rejected():
    with pytest.raises(ValueError):
        build_timings(["Hi."], [], [], [])
