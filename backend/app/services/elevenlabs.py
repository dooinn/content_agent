"""ElevenLabs text-to-speech with character-level timestamps."""

import base64
from dataclasses import dataclass

import httpx


@dataclass
class SpeechResult:
    audio: bytes
    characters: list[str]
    starts: list[float]
    ends: list[float]


class ElevenLabsError(RuntimeError):
    pass


class ElevenLabsClient:
    def __init__(
        self,
        api_key: str,
        model_id: str = "eleven_multilingual_v2",
        base_url: str = "https://api.elevenlabs.io",
        http: httpx.AsyncClient | None = None,
    ):
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.http = http or httpx.AsyncClient(timeout=120.0)
        self.headers = {"xi-api-key": api_key}

    async def aclose(self) -> None:
        await self.http.aclose()

    async def speak(self, text: str, voice_id: str) -> SpeechResult:
        if not voice_id:
            raise ElevenLabsError("no voice id configured (set ELEVENLABS_VOICE_ID)")
        response = await self.http.post(
            f"{self.base_url}/v1/text-to-speech/{voice_id}/with-timestamps",
            params={"output_format": "mp3_44100_128"},
            headers=self.headers,
            json={
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25},
            },
        )
        if response.is_error:
            raise ElevenLabsError(f"TTS failed {response.status_code}: {response.text[:500]}")
        body = response.json()
        alignment = body["alignment"]
        return SpeechResult(
            audio=base64.b64decode(body["audio_base64"]),
            characters=alignment["characters"],
            starts=alignment["character_start_times_seconds"],
            ends=alignment["character_end_times_seconds"],
        )
