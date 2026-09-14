"""Usage capture: model tokens, media units, and latency, recorded where the money is spent.

Provider clients call `record()`. The graph builder opens a collector around each work node and
merges what was recorded into the `usage` state channel, so usage is checkpointed together with
the work it paid for. Outside a collector (scripts, tests of a single client) `record()` is a
no-op.
"""

import dataclasses
import functools
import time
from contextvars import ContextVar

from langgraph.types import Command

_collector: ContextVar[list[dict] | None] = ContextVar("usage_collector", default=None)


def record(kind: str, **fields) -> None:
    events = _collector.get()
    if events is not None:
        events.append({"kind": kind, **fields})


def collect(node: str):
    """Wrap an async graph node so the usage it records lands in the `usage` channel."""

    def decorate(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            events: list[dict] = []
            token = _collector.set(events)  # child tasks share this list through the context
            try:
                result = await fn(*args, **kwargs)
            finally:
                _collector.reset(token)
            if not events:
                return result
            stamped = [{"node": node, "at": round(time.time(), 3), **event} for event in events]
            if isinstance(result, Command):
                update = dict(result.update or {})
                update["usage"] = [*update.get("usage", []), *stamped]
                return dataclasses.replace(result, update=update)
            update = dict(result or {})
            update["usage"] = [*update.get("usage", []), *stamped]
            return update

        return wrapper

    return decorate
