"""Storage helpers including schema migration support."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any

from .protocol import CURRENT_SCHEMA_VERSION, ModelValidationError


_DEF_ARTIFACT_STATUS_MAP = {
    "accepted": "accept",
    "active": "accept",
    "branched": "branch",
    "parked": "park",
    "archived": "park",
    "draft": "park",
    "rejected": "reject",
}

_DEF_DECISION_MAP = {
    "accepted": "accept",
    "commit": "accept",
    "defer": "park",
    "branched": "branch",
    "parked": "park",
    "rejected": "reject",
}

_DEF_ARENA_MAP = {
    "general": "problem_framing",
    "code": "mechanism",
    "policy": "empirical_grounding",
}


def migrate_record(record: dict[str, Any], from_version: int, to_version: int) -> dict[str, Any]:
    """Migrate a serialized record between schema versions.

    The function is intentionally incremental so future schema additions can
    chain migration steps without breaking continuation compatibility.
    """
    if from_version < 1 or to_version < 1:
        raise ModelValidationError("Schema versions must be >= 1")
    if from_version > to_version:
        raise ModelValidationError("Downgrade migrations are not supported")

    migrated = deepcopy(record)
    version = from_version

    while version < to_version:
        step_fn = _MIGRATION_STEPS.get(version)
        if step_fn is None:
            raise ModelValidationError(
                f"No migration step registered from version {version} to {version + 1}"
            )
        migrated = step_fn(migrated)
        version += 1

    migrated["schema_version"] = to_version
    return migrated


def ensure_current_schema(record: dict[str, Any]) -> dict[str, Any]:
    """Return a record upgraded to CURRENT_SCHEMA_VERSION."""
    version = int(record.get("schema_version", 1))
    if version == CURRENT_SCHEMA_VERSION:
        return record
    return migrate_record(record, version, CURRENT_SCHEMA_VERSION)


def _normalize(value: Any) -> str:
    return str(value).strip().lower()


def _migrate_v1_to_v2(record: dict[str, Any]) -> dict[str, Any]:
    """Upgrade enum values to spec-aligned v2 vocabulary."""
    upgraded = deepcopy(record)

    if "status" in upgraded:
        status = _normalize(upgraded["status"])
        upgraded["status"] = _DEF_ARTIFACT_STATUS_MAP.get(status, status)

    if "decision" in upgraded:
        decision = _normalize(upgraded["decision"])
        upgraded["decision"] = _DEF_DECISION_MAP.get(decision, decision)

    if "requested_action" in upgraded:
        action = _normalize(upgraded["requested_action"])
        upgraded["requested_action"] = _DEF_DECISION_MAP.get(action, action)

    if "next_recommended_arena" in upgraded:
        arena = upgraded["next_recommended_arena"]
        if isinstance(arena, list):
            upgraded["next_recommended_arena"] = [
                _DEF_ARENA_MAP.get(_normalize(item), _normalize(item)) for item in arena
            ]
        else:
            normalized = _normalize(arena)
            upgraded["next_recommended_arena"] = _DEF_ARENA_MAP.get(normalized, normalized)

    if "arena" in upgraded:
        arena = _normalize(upgraded["arena"])
        upgraded["arena"] = _DEF_ARENA_MAP.get(arena, arena)

    return upgraded


def _version_from_artifact_id(artifact_id: str) -> str | None:
    match = re.search(r"_v(\d+)$", artifact_id)
    if match is None:
        return None
    return f"v{match.group(1)}"


def _migrate_v2_to_v3(record: dict[str, Any]) -> dict[str, Any]:
    """Add artifact head pointers used by session artifact playback."""
    upgraded = deepcopy(record)

    if "snapshot_id" in upgraded:
        artifact_heads = upgraded.get("artifact_heads")
        if not isinstance(artifact_heads, dict):
            artifact_heads = {}

        lineages = upgraded.get("artifact_lineages")
        if isinstance(lineages, dict):
            for lineage_key, branch in lineages.items():
                if not isinstance(branch, list) or not branch:
                    continue
                latest = str(branch[-1]).strip()
                if not latest:
                    continue
                version = _version_from_artifact_id(latest)
                if not version:
                    continue
                lineage_id = str(lineage_key).strip() or latest
                artifact_heads.setdefault(
                    lineage_id,
                    {
                        "artifact_id": latest,
                        "version": version,
                        "path": f"artifacts/{lineage_id}/{version}.json",
                    },
                )

        if artifact_heads:
            upgraded["artifact_heads"] = artifact_heads

    if "commit_id" in upgraded and "artifact_id" in upgraded and "version" in upgraded:
        artifact_id = str(upgraded.get("artifact_id", "")).strip()
        version = str(upgraded.get("version", "")).strip()
        if artifact_id and version and "artifact_ref" not in upgraded:
            upgraded["artifact_ref"] = f"artifacts/{artifact_id}/{version}.json"

    return upgraded




def analyze_dual_ledger_soul_influence(session_dir: str | Path) -> dict[str, Any]:
    """Compare how different soul profiles map to the same cognitive output."""

    root = Path(session_dir)
    soul_dir = root / "ledgers" / "soul"
    cognitive_dir = root / "ledgers" / "cognitive"

    if not soul_dir.exists() or not cognitive_dir.exists():
        return {
            "cognitive_output_count": 0,
            "comparisons": [],
        }

    cognitive_by_ref: dict[str, dict[str, Any]] = {}
    for path in sorted(cognitive_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            continue
        cognitive_by_ref[path.relative_to(root).as_posix()] = raw

    traces_by_cognitive_ref: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(soul_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            continue
        cognitive_ref = str(raw.get("cognitive_output_ref", "")).strip()
        if not cognitive_ref:
            continue
        traces_by_cognitive_ref.setdefault(cognitive_ref, []).append(raw)

    comparisons: list[dict[str, Any]] = []
    for cognitive_ref, traces in traces_by_cognitive_ref.items():
        if len(traces) < 2:
            continue
        unique_souls: dict[str, dict[str, Any]] = {}
        for trace in traces:
            soul_payload = trace.get("soul_profile", {})
            if not isinstance(soul_payload, dict):
                soul_payload = {}
            soul_key = json.dumps(soul_payload, ensure_ascii=False, sort_keys=True)
            unique_souls[soul_key] = soul_payload

        if len(unique_souls) < 2:
            continue

        comparisons.append(
            {
                "cognitive_output_ref": cognitive_ref,
                "cognitive_output": cognitive_by_ref.get(cognitive_ref, {}),
                "soul_profiles": list(unique_souls.values()),
                "trace_ids": [str(trace.get("soul_trace_id", "")).strip() for trace in traces],
                "trace_count": len(traces),
            }
        )

    return {
        "cognitive_output_count": len(cognitive_by_ref),
        "comparisons": comparisons,
    }


def summarize_session_quality_from_dir(session_dir: str | Path) -> dict[str, Any]:
    """Load one session's event log and summarize round quality trends."""

    event_log_path = Path(session_dir) / "event_log.jsonl"
    if not event_log_path.exists():
        return summarize_session_quality_trends([])

    events: list[dict[str, Any]] = []
    with event_log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = line.strip()
            if not payload:
                continue
            raw = json.loads(payload)
            if isinstance(raw, dict):
                events.append(raw)

    return summarize_session_quality_trends(events)


def summarize_session_quality_trends(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate deliberation round quality metrics into session-level trend statistics."""

    round_events = [
        event
        for event in events
        if isinstance(event, dict)
        and event.get("type") == "deliberation.round"
        and isinstance(event.get("quality_metrics"), dict)
    ]

    if not round_events:
        return {
            "round_count": 0,
            "series": {
                "obligation_completeness": [],
                "critique_independence": [],
                "diversity_score": [],
                "dissent_retained": [],
            },
            "averages": {
                "obligation_completeness": 0.0,
                "critique_independence": 0.0,
                "diversity_score": 0.0,
                "dissent_retained_ratio": 0.0,
            },
        }

    obligation_series: list[float] = []
    independence_series: list[float] = []
    diversity_series: list[float] = []
    dissent_series: list[bool] = []

    for event in round_events:
        metrics = event["quality_metrics"]
        obligation_series.append(float(metrics.get("obligation_completeness", 0.0)))
        independence_series.append(float(metrics.get("critique_independence", 0.0)))
        diversity_series.append(float(metrics.get("diversity_score", 0.0)))
        dissent_series.append(bool(metrics.get("dissent_retained", False)))

    round_count = len(round_events)

    def _avg(values: list[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    return {
        "round_count": round_count,
        "series": {
            "obligation_completeness": obligation_series,
            "critique_independence": independence_series,
            "diversity_score": diversity_series,
            "dissent_retained": dissent_series,
        },
        "averages": {
            "obligation_completeness": _avg(obligation_series),
            "critique_independence": _avg(independence_series),
            "diversity_score": _avg(diversity_series),
            "dissent_retained_ratio": round(sum(1 for item in dissent_series if item) / round_count, 4),
        },
    }


_MIGRATION_STEPS = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
}
