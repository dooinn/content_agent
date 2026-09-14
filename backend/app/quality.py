"""Quality and cost metrics, read back from LangGraph checkpoints.

- Review decisions come from the checkpointer's pending writes: each gate leaves its interrupt
  payload (the stage) and the resume value (the reviewer's decision) on the same checkpoint, so
  every project ever run is covered without extra logging.
- Critic reports, fact-check stats, and generated assets come from the state history.
- Token spend comes from the `usage` channel, which exists since usage capture was added; older
  projects report their media units but no Claude cost.
"""

import json
from collections import Counter

from app.pricing import llm_cost

INTERRUPT, RESUME = "__interrupt__", "__resume__"
FIRST_TRY = {"approve", "select"}
REWORK = {"revise", "regenerate"}
STAGES = [
    "research", "angle", "script", "audio", "bible", "scenes",
    "keyframes", "preview", "motion", "clips", "final",
]  # fmt: skip
FINISHED = {"done", "final_ready"}


def _first(value):
    return value[-1] if isinstance(value, list | tuple) and value else value


async def review_decisions(checkpointer, thread_id: str) -> list[dict]:
    """Every gate decision on a project, oldest first."""
    stages: dict[str, tuple[str, str]] = {}
    decisions: dict[str, dict] = {}
    async for tup in checkpointer.alist({"configurable": {"thread_id": thread_id}}):
        checkpoint_id = tup.config["configurable"]["checkpoint_id"]
        for _task_id, channel, value in tup.pending_writes or []:
            if channel == INTERRUPT:
                payload = getattr(_first(value), "value", _first(value))
                if isinstance(payload, dict) and "stage" in payload:
                    stages[checkpoint_id] = (payload["stage"], tup.checkpoint.get("ts", ""))
            elif channel == RESUME and isinstance(_first(value), dict):
                decisions[checkpoint_id] = _first(value)
    rows = [
        {
            "stage": stages[checkpoint_id][0],
            "at": stages[checkpoint_id][1],
            "action": decision.get("action"),
            "feedback": bool(decision.get("feedback")),
            "edits": sorted((decision.get("edits") or {}).keys()),
        }
        for checkpoint_id, decision in decisions.items()
        if checkpoint_id in stages
    ]
    return sorted(rows, key=lambda row: row["at"])


def _reviews(decisions: list[dict]) -> dict:
    by_stage: dict[str, dict] = {}
    for row in decisions:
        stage = by_stage.setdefault(
            row["stage"], {"decisions": 0, "first_try": row["action"] in FIRST_TRY, "actions": {}}
        )
        stage["decisions"] += 1
        stage["actions"][row["action"]] = stage["actions"].get(row["action"], 0) + 1
    visited = [by_stage[s] for s in STAGES if s in by_stage]
    return {
        "decisions": len(decisions),
        "rework": sum(1 for row in decisions if row["action"] in REWORK),
        "with_feedback": sum(1 for row in decisions if row["feedback"]),
        "first_try_rate": sum(s["first_try"] for s in visited) / len(visited) if visited else None,
        "by_stage": {s: by_stage[s] for s in STAGES if s in by_stage},
    }


def _changes(snapshots: list[dict], field: str) -> list:
    """Successive distinct values of a state field, oldest first."""
    values, last = [], None
    for values_at in snapshots:
        value = values_at.get(field)
        encoded = json.dumps(value, sort_keys=True, default=str)
        if value is not None and encoded != last:
            values.append(value)
        last = encoded
    return values


def _fact_checks(snapshots: list[dict], latest: dict) -> dict:
    runs: dict[str, list[dict]] = {}
    for stats in _changes(snapshots, "fact_check_stats"):
        for stage, entry in stats.items():
            if not runs.get(stage) or runs[stage][-1] != entry:
                runs.setdefault(stage, []).append(entry)
    result = {}
    for stage in ("angles", "script"):
        report = (latest.get("fact_checks") or {}).get(stage)
        if stage not in runs and report is None:
            continue
        stage_runs = runs.get(stage, [])
        result[stage] = {
            "runs": len(stage_runs),
            "drafts": sum(run["drafts"] for run in stage_runs),
            "first_draft_issues": sum(run["issues_per_draft"][0] for run in stage_runs),
            "clean_first_drafts": sum(run["issues_per_draft"][0] == 0 for run in stage_runs),
            "final_passed": report["passed"] if report else None,
        }
    return result


def _critic(snapshots: list[dict]) -> dict | None:
    reports = []
    last = None
    for values in snapshots:
        key = (values.get("critic_rounds"), json.dumps(values.get("critic_report"), sort_keys=True))
        if values.get("critic_report") is not None and key != last:
            reports.append(values["critic_report"])
        last = key
    if not reports:
        return None
    categories = Counter(issue["category"] for r in reports for issue in r.get("issues", []))
    return {
        "reports": len(reports),
        "reports_with_issues": sum(1 for r in reports if r.get("issues")),
        "issues_found": sum(len(r.get("issues", [])) for r in reports),
        "categories": dict(categories.most_common()),
        "final_passed": bool(reports[-1].get("passed") or not reports[-1].get("issues")),
    }


def _media(snapshots: list[dict], latest: dict) -> dict:
    keyframes, refs, clips, narrations, music = set(), set(), set(), set(), {}
    for values in snapshots:
        for keys in (values.get("keyframes") or {}).values():
            keyframes.update(keys)
        refs.update((values.get("character_refs") or {}).values())
        for order, keys in (values.get("clips") or {}).items():
            clips.update((order, key) for key in keys)
        if narration := values.get("narration"):
            narrations.add(narration["audio_key"])
        if bgm := values.get("bgm"):
            music[bgm["audio_key"]] = bgm.get("seconds", 0)
    seconds = {str(s["order"]): s.get("clip_seconds", 0) for s in latest.get("scenes") or []}
    return {
        "images": len(keyframes) + len(refs),
        "keyframes": len(keyframes),
        "character_sheets": len(refs),
        "clips": len(clips),
        "clip_seconds": sum(seconds.get(order, 0) for order, _ in clips),
        "narration_takes": len(narrations),
        "music_tracks": len(music),
        "music_seconds": sum(music.values()),
    }


def _llm(events: list[dict]) -> dict | None:
    calls = [event for event in events if event.get("kind") == "llm"]
    if not calls:
        return None
    by_node: dict[str, float] = {}
    for call in calls:
        by_node[call.get("node", "?")] = by_node.get(call.get("node", "?"), 0) + (
            llm_cost(call) or 0
        )
    return {
        "calls": len(calls),
        "input_tokens": sum(c.get("input_tokens", 0) for c in calls),
        "output_tokens": sum(c.get("output_tokens", 0) for c in calls),
        "web_searches": sum(c.get("web_searches", 0) for c in calls),
        "cost_usd": round(sum(llm_cost(c) or 0 for c in calls), 4),
        "unpriced_calls": sum(1 for c in calls if llm_cost(c) is None),
        "cost_by_node": {node: round(cost, 4) for node, cost in by_node.items()},
    }


async def project_metrics(graph, record) -> dict:
    config = {"configurable": {"thread_id": record.id}}
    snapshots = [snap.values async for snap in graph.aget_state_history(config)]
    snapshots.reverse()  # oldest first
    latest = snapshots[-1] if snapshots else {}
    return {
        "project_id": record.id,
        "topic": record.topic,
        "status": record.status,
        "target_seconds": latest.get("target_seconds") or 30,
        "reviews": _reviews(await review_decisions(graph.checkpointer, record.id)),
        "fact_check": _fact_checks(snapshots, latest),
        "critic": _critic(snapshots),
        "media": _media(snapshots, latest),
        "llm": _llm(latest.get("usage") or []),
    }


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarize(projects: list[dict]) -> dict:
    stages = []
    for stage in STAGES:
        entries = [p["reviews"]["by_stage"][stage] for p in projects
                   if stage in p["reviews"]["by_stage"]]  # fmt: skip
        if entries:
            stages.append({
                "stage": stage,
                "projects": len(entries),
                "first_try_rate": _mean([e["first_try"] for e in entries]),
                "rework_per_project": _mean([
                    sum(n for a, n in e["actions"].items() if a in REWORK) for e in entries
                ]),
            })
    fact_runs = [fc for p in projects for fc in p["fact_check"].values() if fc["runs"]]
    critics = [p["critic"] for p in projects if p["critic"]]
    categories: Counter = Counter()
    for critic in critics:
        categories.update(critic["categories"])
    priced = [p for p in projects if p["llm"]]
    finished = [p for p in projects if p["status"] in FINISHED]
    return {
        "projects": len(projects),
        "finished": len(finished),
        "first_try_rate": _mean([
            e["first_try"] for p in projects for e in p["reviews"]["by_stage"].values()
        ]),
        "stages": stages,
        "fact_check": {
            "runs": sum(fc["runs"] for fc in fact_runs),
            "clean_first_draft_rate": (
                sum(fc["clean_first_drafts"] for fc in fact_runs)
                / sum(fc["runs"] for fc in fact_runs)
                if fact_runs else None
            ),
            "drafts_per_run": (
                sum(fc["drafts"] for fc in fact_runs) / sum(fc["runs"] for fc in fact_runs)
                if fact_runs else None
            ),
            "issues_caught": sum(fc["first_draft_issues"] for fc in fact_runs),
        },
        "critic": {
            "projects": len(critics),
            "issues_found": sum(c["issues_found"] for c in critics),
            "issues_per_project": _mean([c["issues_found"] for c in critics]),
            "categories": dict(categories.most_common()),
        },
        "cost": {
            "tracked_projects": len(priced),
            "claude_usd_total": round(sum(p["llm"]["cost_usd"] for p in priced), 4),
            "claude_usd_per_project": _mean([p["llm"]["cost_usd"] for p in priced]),
        },
        "media_per_finished": {
            "images": _mean([p["media"]["images"] for p in finished]),
            "clip_seconds": _mean([p["media"]["clip_seconds"] for p in finished]),
        },
    }
