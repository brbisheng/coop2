"""Perspective module protocol and basic stubs."""

from __future__ import annotations

from typing import Any, Protocol


REQUIRED_AUDIT_FIELDS = (
    "observations",
    "criticisms",
    "revisions",
    "risks",
    "questions",
    "evidence_needs",
    "confidence",
)


class PerspectiveValidationError(ValueError):
    """Raised when a perspective audit payload is invalid."""


class PerspectiveModule(Protocol):
    name: str
    version: str

    def audit(
        self,
        artifact: dict[str, Any],
        local_context: dict[str, Any],
        unresolved_conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ...


def validate_perspective_output(payload: dict[str, Any]) -> None:
    """Validate required perspective output envelope fields."""

    missing = [field for field in REQUIRED_AUDIT_FIELDS if field not in payload]
    if missing:
        raise PerspectiveValidationError(f"Missing required audit fields: {missing}")

    if not isinstance(payload["confidence"], (int, float)):
        raise PerspectiveValidationError("confidence must be numeric")


class EconomicsModuleStub:
    """Minimal economics perspective stub used for MVP wiring tests."""

    name = "economics"
    version = "0.1"

    def audit(
        self,
        artifact: dict[str, Any],
        local_context: dict[str, Any],
        unresolved_conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {
            "observations": ["incentives appear mixed"],
            "criticisms": ["identification strategy may be weak"],
            "revisions": ["clarify mechanism assumptions"],
            "risks": ["strategic response bias"],
            "questions": ["what is the credible observable proxy?"],
            "evidence_needs": ["collect baseline behavioral indicators"],
            "confidence": 0.55,
        }
        validate_perspective_output(payload)
        return payload
