"""Storage helpers including schema migration support."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .protocol import CURRENT_SCHEMA_VERSION, ModelValidationError


_DEF_ARTIFACT_STATUS_MAP = {
    "archived": "parked",
}

_DEF_DECISION_MAP = {
    "commit": "accept",
    "defer": "park",
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


_MIGRATION_STEPS = {
    1: _migrate_v1_to_v2,
}
