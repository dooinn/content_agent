import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Load .env into the process so the Anthropic and Langfuse SDKs see their keys too.
load_dotenv()

from app.api.routes import router  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.graph.builder import build_graph, open_checkpointer  # noqa: E402
from app.graph.state import Deps  # noqa: E402
from app.llm.claude import Claude  # noqa: E402
from app.observability import flush, setup_tracing  # noqa: E402
from app.runtime import ProjectRegistry, ProjectRunner  # noqa: E402
from app.services.elevenlabs import ElevenLabsClient  # noqa: E402
from app.services.magnific import MagnificClient  # noqa: E402
from app.services.render import PreviewRenderer  # noqa: E402
from app.services.storage import build_storage  # noqa: E402

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tracing()
    storage = build_storage(settings)
    deps = Deps(
        settings=settings,
        claude=Claude(settings.claude_model, settings.anthropic_api_key),
        magnific=MagnificClient(
            settings.magnific_api_key,
            settings.magnific_base_url,
            settings.magnific_poll_interval_s,
            settings.magnific_task_timeout_s,
            settings.video_task_timeout_s,
        ),
        tts=ElevenLabsClient(
            settings.elevenlabs_api_key, settings.elevenlabs_model_id, settings.elevenlabs_base_url
        ),
        storage=storage,
        renderer=PreviewRenderer(settings.ffmpeg_bin, settings.bgm_volume),
    )
    async with open_checkpointer(settings) as checkpointer:
        app.state.runner = ProjectRunner(build_graph(deps, checkpointer), ProjectRegistry(storage))
        yield
    await deps.magnific.aclose()
    await deps.tts.aclose()
    flush()


app = FastAPI(title="History Shorts Agent", version="0.1.0", lifespan=lifespan)
app.include_router(router)

if settings.storage_backend == "local":
    settings.local_storage_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=settings.local_storage_dir), name="files")
