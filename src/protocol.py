"""Protocol-layer primitives for unified deliberation data models."""

from __future__ import annotations

from enum import Enum


CURRENT_SCHEMA_VERSION = 1


class ModelValidationError(ValueError):
    """Raised when a record does not satisfy model constraints."""


class ArtifactStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class DebateDecision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    DEFER = "defer"


class DebateArena(str, Enum):
    GENERAL = "general"
    CODE = "code"
    POLICY = "policy"


class CommitStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    REVERTED = "reverted"


def parse_enum(raw_value: str, enum_type: type[Enum], field_name: str) -> Enum:
    """Parse/validate enum values with a clear error message."""
    try:
        return enum_type(raw_value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ModelValidationError(
            f"Invalid value for '{field_name}': {raw_value!r}. Allowed: {allowed}."
        ) from exc
