"""Storage helpers including schema migration support."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .protocol import CURRENT_SCHEMA_VERSION, ModelValidationError


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


def _migrate_v1_to_v2(record: dict[str, Any]) -> dict[str, Any]:
    """Placeholder future migration.

    Example strategy:
    - introduce new optional field defaults
    - rename keys while preserving old aliases
    """
    upgraded = deepcopy(record)
    upgraded.setdefault("metadata", {})
    return upgraded


_MIGRATION_STEPS = {
    # 1: _migrate_v1_to_v2,
}
