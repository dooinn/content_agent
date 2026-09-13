"""Optional Langfuse tracing. Everything is a no-op unless LANGFUSE_* keys are set."""

import functools
import os
from collections.abc import Iterator
from contextlib import contextmanager

_enabled = False


def setup_tracing() -> bool:
    global _enabled
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return False
    from langfuse import get_client
    from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

    get_client()
    AnthropicInstrumentor().instrument()
    _enabled = True
    return True


def traced(name: str):
    """Wrap an async graph node in a Langfuse span."""

    def decorate(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            if not _enabled:
                return await fn(*args, **kwargs)
            from langfuse import get_client

            with get_client().start_as_current_observation(name=name):
                return await fn(*args, **kwargs)

        return wrapper

    return decorate


@contextmanager
def project_trace(project_id: str, stage: str) -> Iterator[None]:
    """One trace per graph run, grouped into a Langfuse session per project."""
    if not _enabled:
        yield
        return
    from langfuse import get_client, propagate_attributes

    with get_client().start_as_current_observation(name=f"run:{stage}"):
        with propagate_attributes(
            session_id=project_id, trace_name=f"shorts:{stage}", tags=["shorts-agent"]
        ):
            yield


def flush() -> None:
    if _enabled:
        from langfuse import get_client

        get_client().flush()
