"""Renderer: scene images or video clips, narration, ducked music, burned-in captions.

Image scenes get a slow push-in (the animatic); video scenes are fitted and trimmed to the
narration timing (the final cut).
"""

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.domain.models import WordTiming

WIDTH, HEIGHT, FPS = 1080, 1920, 30
DEFAULT_BGM_VOLUME = 0.2
PUNCTUATION = (".", ",", "!", "?", ";", ":")

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, \
Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, \
Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,\
2,80,80,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


class RenderError(RuntimeError):
    pass


@dataclass
class SceneClip:
    path: str
    duration: float
    kind: Literal["image", "video"] = "image"


def group_caption_words(
    words: list[WordTiming], max_words: int = 3, max_gap: float = 0.35
) -> list[list[WordTiming]]:
    groups: list[list[WordTiming]] = []
    current: list[WordTiming] = []
    for word in words:
        if current and (len(current) >= max_words or word.start - current[-1].end > max_gap):
            groups.append(current)
            current = []
        current.append(word)
        if word.text.endswith(PUNCTUATION):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def ass_time(seconds: float) -> str:
    centis = max(0, round(seconds * 100))
    hours, rest = divmod(centis, 360_000)
    minutes, rest = divmod(rest, 6_000)
    secs, centis = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def build_captions(words: list[WordTiming]) -> str:
    groups = group_caption_words(words)
    lines = [ASS_HEADER]
    for i, group in enumerate(groups):
        start, end = group[0].start, group[-1].end
        # Hold a caption until the next one when the pause is short, to avoid flicker.
        if i + 1 < len(groups) and groups[i + 1][0].start - end < 0.3:
            end = groups[i + 1][0].start
        text = " ".join(w.text for w in group).replace("{", "(").replace("}", ")")
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{text}")
    return "\n".join(lines) + "\n"


def _scene_filter(index: int, clip: SceneClip) -> str:
    if clip.kind == "video":
        # Fill the frame, hold the last frame if the clip runs short, then trim to the scene.
        return (
            f"[{index}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1,"
            f"tpad=stop_mode=clone:stop_duration={clip.duration:.3f},"
            f"trim=duration={clip.duration:.3f},setpts=PTS-STARTPTS[v{index}]"
        )
    work_w, work_h = WIDTH * 3 // 2, HEIGHT * 3 // 2
    frames = max(1, round(clip.duration * FPS))
    return (
        f"[{index}:v]scale={work_w}:{work_h}:force_original_aspect_ratio=increase,"
        f"crop={work_w}:{work_h},"
        f"zoompan=z='min(1+0.0007*on,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},setsar=1[v{index}]"
    )


def build_command(
    ffmpeg: str,
    clips: list[SceneClip],
    narration: str,
    bgm: str | None,
    captions: str,
    total: float,
    output: str,
    bgm_volume: float = DEFAULT_BGM_VOLUME,
) -> list[str]:
    """All paths are relative to the render working directory."""
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    for clip in clips:
        cmd += ["-i", clip.path]
    cmd += ["-i", narration]
    if bgm:
        cmd += ["-i", bgm]

    n = len(clips)
    filters = [_scene_filter(i, clip) for i, clip in enumerate(clips)]
    filters.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vcat]")
    filters.append(f"[vcat]subtitles={captions},format=yuv420p[vout]")

    # Mix in stereo (narration is mono) and resample at the end: loudnorm works at 192 kHz
    # internally, and the encoder would otherwise keep a non-standard rate.
    stereo = "aformat=sample_rates=48000:channel_layouts=stereo"
    master = f"loudnorm=I=-14:TP=-1.5:LRA=11,{stereo}"
    if bgm:
        filters += [
            f"[{n}:a]{stereo},apad=whole_dur={total:.3f},asplit=2[voice][key]",
            f"[{n + 1}:a]{stereo},atrim=0:{total:.3f},volume={bgm_volume}[bed]",
            "[bed][key]sidechaincompress=threshold=0.02:ratio=12:attack=15:release=400[duck]",
            f"[voice][duck]amix=inputs=2:duration=first:normalize=0,{master}[aout]",
        ]
    else:
        filters.append(f"[{n}:a]{stereo},apad=whole_dur={total:.3f},{master}[aout]")

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        output,
    ]  # fmt: skip
    return cmd


class PreviewRenderer:
    def __init__(self, ffmpeg: str = "ffmpeg", bgm_volume: float = DEFAULT_BGM_VOLUME):
        self.ffmpeg = ffmpeg
        self.bgm_volume = bgm_volume

    async def render(
        self,
        workdir: Path,
        clips: list[SceneClip],
        narration: str,
        bgm: str | None,
        words: list[WordTiming],
        total: float,
        output: str = "preview.mp4",
    ) -> Path:
        (workdir / "captions.ass").write_text(build_captions(words), encoding="utf-8")
        cmd = build_command(
            self.ffmpeg, clips, narration, bgm, "captions.ass", total, output,
            bgm_volume=self.bgm_volume,
        )
        # subprocess.run in a thread works on any event loop, including Windows selector loops.
        result = await asyncio.to_thread(
            subprocess.run, cmd, cwd=workdir, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RenderError(result.stderr[-2000:])
        return workdir / output
