from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ImageModel = Literal["gpt-image-2", "seedream"]
ImageQuality = Literal["low", "medium", "high"]
VideoModel = Literal["kling-v3-pro", "kling-v3-std", "kling-v3-turbo"]


class Settings(BaseSettings):
    """Server defaults. Image model, image quality, video model, and caption style can be
    overridden per project."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Claude
    anthropic_api_key: str | None = None
    claude_model: str = "claude-sonnet-5"

    # Magnific (formerly Freepik) — images, video, music
    magnific_api_key: str = ""
    magnific_base_url: str = "https://api.magnific.com"
    magnific_poll_interval_s: float = 4.0
    magnific_task_timeout_s: float = 600.0
    image_model: ImageModel = "gpt-image-2"
    image_quality: ImageQuality = "high"
    keyframe_candidates: int = 2
    image_concurrency: int = 4

    # Image-to-video: Kling 3 via Magnific
    video_model: VideoModel = "kling-v3-pro"
    video_concurrency: int = 3
    video_task_timeout_s: float = 1200.0
    clip_candidates: int = 1
    video_negative_prompt: str = (
        "text, subtitles, watermark, morphing, distorted face, extra limbs, flicker, scene cut, "
        "blur, low quality"
    )

    # ElevenLabs — narration
    elevenlabs_api_key: str = ""
    elevenlabs_base_url: str = "https://api.elevenlabs.io"
    elevenlabs_voice_id: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    # Storage
    storage_backend: Literal["local", "gcs"] = "local"
    local_storage_dir: Path = Path("data")
    gcs_bucket: str = ""

    # LangGraph checkpoints
    checkpointer: Literal["memory", "postgres"] = "postgres"
    database_url: str = "postgresql://shorts:shorts@localhost:5433/shorts"

    # Pipeline rules
    max_critic_rounds: int = 2
    max_fact_rewrites: int = 2
    bgm_volume: float = 0.2
    min_years_since_death: int = 75
    ffmpeg_bin: str = "ffmpeg"


@lru_cache
def get_settings() -> Settings:
    return Settings()
