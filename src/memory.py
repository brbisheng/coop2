"""Memory retrieval primitives for continuation workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ContinuationPack:
    """Minimal context package used to continue an existing session."""

    goal: str
    target_artifact_id: str
    arena: str | None
    minimal_context: dict[str, Any]
    unresolved_conflicts: list[dict[str, Any]]


def snapshot_priority_fields(snapshot: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    """Extract continuation hints from snapshot.json.

    Returns:
        (priority_open_issues, next_recommended_arena)
    """

    raw_issues = snapshot.get("priority_open_issues", [])
    if not isinstance(raw_issues, list):
        raw_issues = []
    issues = [issue for issue in raw_issues if isinstance(issue, dict)]

    arena = snapshot.get("next_recommended_arena")
    if arena is not None:
        arena = str(arena)
    return issues, arena


def _lineage_set(snapshot: dict[str, Any], target_artifact_id: str) -> set[str]:
    lineage: set[str] = {target_artifact_id}

    raw_lineages = snapshot.get("artifact_lineages", {})
    if isinstance(raw_lineages, dict):
        branch = raw_lineages.get(target_artifact_id, [])
        if isinstance(branch, list):
            lineage.update(str(item) for item in branch if str(item).strip())

    artifacts = snapshot.get("artifacts", [])
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            aid = str(artifact.get("artifact_id", "")).strip()
            if not aid:
                continue
            parent = str(artifact.get("parent_artifact_id", "")).strip()
            if aid == target_artifact_id or parent in lineage:
                lineage.add(aid)
            if aid in lineage and parent:
                lineage.add(parent)

    return lineage


def _entry_lineage_refs(entry: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    keys = (
        "artifact_id",
        "target_artifact_id",
        "parent_artifact_id",
        "lineage_id",
        "lineage_root",
    )
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            refs.add(value.strip())

    for list_key in ("artifact_ids", "lineage_ids", "target_artifact_ids"):
        value = entry.get(list_key)
        if isinstance(value, list):
            refs.update(str(item).strip() for item in value if str(item).strip())

    return refs


def _is_related(entry: dict[str, Any], lineage: set[str]) -> bool:
    return bool(_entry_lineage_refs(entry) & lineage)


def _is_unresolved_dissent(entry: dict[str, Any]) -> bool:
    status = str(entry.get("status", "")).strip().lower()
    if status in {"open", "unresolved", "pending"}:
        return True
    if entry.get("resolved") is False:
        return True
    return False


def _apply_budget(
    recent_related: list[dict[str, Any]],
    key_nodes: list[dict[str, Any]],
    recent_k: int,
    entry_budget: int,
) -> list[dict[str, Any]]:
    selected = recent_related[-recent_k:] if recent_k > 0 else []
    selected_ids = {id(item) for item in selected}

    for item in key_nodes:
        if id(item) not in selected_ids:
            selected.append(item)
            selected_ids.add(id(item))

    if entry_budget > 0 and len(selected) > entry_budget:
        key_ids = {id(item) for item in key_nodes}
        keep = [item for item in selected if id(item) in key_ids]
        free_budget = max(entry_budget - len(keep), 0)
        recent_keep = [item for item in selected if id(item) not in key_ids][-free_budget:]
        selected = recent_keep + keep

    return selected


def build_minimal_context(
    snapshot: dict[str, Any],
    target_artifact_id: str,
    commits: list[dict[str, Any]],
    dissents: list[dict[str, Any]],
    events: list[dict[str, Any]],
    *,
    recent_k: int = 20,
    entry_budget: int = 120,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build continuation context with lineage filtering + budget trimming.

    Strategy:
    1) read snapshot priority fields,
    2) keep only entries tied to target lineage,
    3) keep recent K plus unresolved dissent key-nodes under a total budget.
    """

    priority_open_issues, next_arena = snapshot_priority_fields(snapshot)
    lineage = _lineage_set(snapshot, target_artifact_id)

    related_commits = [entry for entry in commits if _is_related(entry, lineage)]
    related_dissents = [entry for entry in dissents if _is_related(entry, lineage)]
    related_events = [entry for entry in events if _is_related(entry, lineage)]

    unresolved = [entry for entry in related_dissents if _is_unresolved_dissent(entry)]

    # Reserve budget equally for the three streams while always retaining unresolved dissent nodes.
    stream_budget = max(entry_budget // 3, 1)
    trimmed_commits = _apply_budget(related_commits, [], recent_k, stream_budget)
    trimmed_events = _apply_budget(related_events, [], recent_k, stream_budget)
    trimmed_dissents = _apply_budget(related_dissents, unresolved, recent_k, stream_budget)

    context = {
        "priority_open_issues": priority_open_issues,
        "next_recommended_arena": next_arena,
        "target_lineage": sorted(lineage),
        "commits": trimmed_commits,
        "dissents": trimmed_dissents,
        "events": trimmed_events,
    }
    return context, unresolved
