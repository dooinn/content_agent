from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.config import Settings
from app.graph.pipeline import Pipeline
from app.graph.state import Deps, ProjectState
from app.observability import traced
from app.usage import collect

# work node -> the gate that reviews it
REVIEWED_BY = {
    "research": "gate_research",
    "angles": "gate_angle",
    "script": "gate_script",
    "audio": "gate_audio",
    "bible": "gate_bible",
    "keyframes": "gate_keyframes",
    "preview": "gate_preview",
    "motion": "gate_motion",
    "clips": "gate_clips",
    "final": "gate_final",
}

# gate -> nodes it can route to
GATE_ROUTES = {
    "gate_research": ("research", "angles", END),
    "gate_angle": ("angles", "script"),
    "gate_script": ("script", "audio"),
    "gate_audio": ("audio", "bible"),
    "gate_bible": ("bible", "scenes"),
    "gate_scenes": ("scenes", "keyframes"),
    "gate_keyframes": ("keyframes", "preview"),
    "gate_preview": ("keyframes", "preview", "motion"),
    "gate_motion": ("motion", "clips"),
    "gate_clips": ("clips", "final"),
    "gate_final": ("final", END),
}


def build_graph(deps: Deps, checkpointer: BaseCheckpointSaver):
    p = Pipeline(deps)
    graph = StateGraph(ProjectState)

    for name in (*REVIEWED_BY, "scenes"):
        graph.add_node(name, traced(f"node:{name}")(collect(name)(getattr(p, name))))
    graph.add_node(
        "critic",
        traced("node:critic")(collect("critic")(p.critic)),
        destinations=("scenes", "gate_scenes"),
    )
    for gate, routes in GATE_ROUTES.items():
        graph.add_node(gate, getattr(p, gate), destinations=routes)

    graph.add_edge(START, "research")
    for work, gate in REVIEWED_BY.items():
        graph.add_edge(work, gate)
    graph.add_edge("scenes", "critic")
    return graph.compile(checkpointer=checkpointer)


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncIterator[BaseCheckpointSaver]:
    if settings.checkpointer == "memory":
        yield InMemorySaver()
        return
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as saver:
        await saver.setup()
        yield saver
