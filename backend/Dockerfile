# Agent API for Cloud Run. Runs as a sidecar next to the review console. Cloud Run routes
# outside traffic only to the console's port, so the console's rewrites are the API's sole
# entry point; it binds 0.0.0.0 so Cloud Run's startup probe can reach it.
FROM python:3.12-slim

# FFmpeg with libass renders the animatic and final cut.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY assets ./assets
ENV PATH="/app/.venv/bin:$PATH" \
    STORAGE_BACKEND=gcs \
    CHECKPOINTER=postgres

RUN useradd --create-home agent
USER agent
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
