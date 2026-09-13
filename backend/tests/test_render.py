import shutil
import subprocess
from pathlib import Path

import pytest

from app.domain.models import WordTiming
from app.services.render import (
    PreviewRenderer,
    SceneClip,
    ass_time,
    build_captions,
    build_command,
    group_caption_words,
)


def words(*items: tuple[str, float, float]) -> list[WordTiming]:
    return [WordTiming(text=t, start=s, end=e) for t, s, e in items]


def test_captions_break_on_punctuation_word_count_and_pauses():
    timed = words(
        ("He", 0.0, 0.2), ("lost.", 0.2, 0.5),
        ("Then", 0.6, 0.8), ("he", 0.8, 0.9), ("won", 0.9, 1.1), ("again", 1.1, 1.4),
        ("later", 2.5, 2.9),
    )
    groups = [[w.text for w in g] for g in group_caption_words(timed)]
    assert groups == [["He", "lost."], ["Then", "he", "won"], ["again"], ["later"]]


def test_ass_time_format():
    assert ass_time(3661.5) == "1:01:01.50"
    assert ass_time(-1) == "0:00:00.00"


def test_captions_escape_override_braces():
    ass = build_captions(words(("{bold}", 0.0, 0.5)))
    assert "(bold)" in ass and "{bold}" not in ass.split("[Events]")[1]


def test_command_ducks_music_only_when_present():
    clips = [SceneClip("a.png", 2.0), SceneClip("b.png", 3.0)]
    with_bgm = " ".join(build_command("ffmpeg", clips, "n.mp3", "m.mp3", "c.ass", 5.0, "o.mp4"))
    without = " ".join(build_command("ffmpeg", clips, "n.mp3", None, "c.ass", 5.0, "o.mp4"))
    assert "sidechaincompress" in with_bgm and "concat=n=2" in with_bgm
    assert "volume=0.2[bed]" in with_bgm
    assert "sidechaincompress" not in without
    quieter = " ".join(
        build_command("ffmpeg", clips, "n.mp3", "m.mp3", "c.ass", 5.0, "o.mp4", bgm_volume=0.1)
    )
    assert "volume=0.1[bed]" in quieter
    assert ":d=60:" in with_bgm and ":d=90:" in with_bgm


def test_video_scenes_are_fitted_and_trimmed_instead_of_zoomed():
    clips = [SceneClip("a.mp4", 4.5, "video"), SceneClip("b.png", 2.0)]
    filters = build_command("ffmpeg", clips, "n.mp3", None, "c.ass", 6.5, "o.mp4")
    graph = filters[filters.index("-filter_complex") + 1].split(";")
    assert "tpad=stop_mode=clone:stop_duration=4.500" in graph[0]
    assert "trim=duration=4.500" in graph[0] and "zoompan" not in graph[0]
    assert "zoompan" in graph[1]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
async def test_render_produces_a_vertical_video(tmp_path: Path):
    def ff(*args: str) -> None:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], cwd=tmp_path, check=True)

    ff("-f", "lavfi", "-i", "color=c=navy:s=720x1280", "-frames:v", "1", "a.png")
    ff("-f", "lavfi", "-i", "color=c=maroon:s=900x900", "-frames:v", "1", "b.png")
    ff("-f", "lavfi", "-i", "sine=frequency=220:duration=2.5", "narration.mp3")
    ff("-f", "lavfi", "-i", "sine=frequency=440:duration=6", "bgm.mp3")

    clips = [SceneClip("a.png", 1.5), SceneClip("b.png", 1.5)]
    timed = words(("Hello", 0.1, 0.6), ("world.", 0.7, 1.2), ("Again.", 1.6, 2.2))
    output = await PreviewRenderer().render(tmp_path, clips, "narration.mp3", "bgm.mp3", timed, 3.0)

    probe = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "stream=codec_type,width,height,sample_rate,channels:format=duration",
         "-of", "default=noprint_wrappers=1", str(output)],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "width=1080" in probe and "height=1920" in probe and "codec_type=audio" in probe
    assert "sample_rate=48000" in probe and "channels=2" in probe
    duration = float(probe.split("duration=")[1].split()[0])
    assert duration == pytest.approx(3.0, abs=0.2)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
async def test_render_final_cut_from_video_clips(tmp_path: Path):
    def ff(*args: str) -> None:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], cwd=tmp_path, check=True)

    # A clip shorter than its scene (held on the last frame) and one longer (trimmed).
    ff("-f", "lavfi", "-i", "testsrc=size=720x1280:rate=24:duration=1.5", "short.mp4")
    ff("-f", "lavfi", "-i", "testsrc=size=1280x720:rate=24:duration=4", "long.mp4")
    ff("-f", "lavfi", "-i", "sine=frequency=220:duration=3.5", "narration.mp3")

    clips = [SceneClip("short.mp4", 2.0, "video"), SceneClip("long.mp4", 2.0, "video")]
    timed = words(("Clip", 0.1, 0.6), ("cut.", 0.7, 1.2))
    output = await PreviewRenderer().render(
        tmp_path, clips, "narration.mp3", None, timed, 4.0, output="final.mp4"
    )

    assert output.name == "final.mp4"
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height:format=duration",
         "-of", "default=noprint_wrappers=1", str(output)],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "width=1080" in probe and "height=1920" in probe
    assert float(probe.split("duration=")[1].split()[0]) == pytest.approx(4.0, abs=0.2)
