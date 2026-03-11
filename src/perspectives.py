"""Perspective module protocol, registry, and MVP perspective implementations."""

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


class BasePerspectiveModule:
    """Simple reusable base with shared payload validation."""

    name = "base"
    version = "0.1"

    def _validated(self, payload: dict[str, Any]) -> dict[str, Any]:
        validate_perspective_output(payload)
        return payload


def validate_perspective_output(payload: dict[str, Any]) -> None:
    """Validate required perspective output envelope fields."""

    missing = [field for field in REQUIRED_AUDIT_FIELDS if field not in payload]
    if missing:
        raise PerspectiveValidationError(f"Missing required audit fields: {missing}")

    if not isinstance(payload["confidence"], (int, float)):
        raise PerspectiveValidationError("confidence must be numeric")


class EconomicsModule(BasePerspectiveModule):
    """Economics perspective for incentives and mechanism quality."""

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
        return self._validated(payload)


class PhilosophyModule(BasePerspectiveModule):
    """Philosophy perspective for normative and conceptual checks."""

    name = "philosophy"
    version = "0.1"

    def audit(
        self,
        artifact: dict[str, Any],
        local_context: dict[str, Any],
        unresolved_conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {
            "observations": ["core concepts are defined but norm hierarchy is implicit"],
            "criticisms": ["value tradeoff assumptions are not explicit"],
            "revisions": ["state ethical priority rule for conflict cases"],
            "risks": ["hidden normative bias in objective selection"],
            "questions": ["which fairness principle governs edge cases?"],
            "evidence_needs": ["document stakeholder value constraints"],
            "confidence": 0.58,
        }
        return self._validated(payload)


class PsychologyModule(BasePerspectiveModule):
    """Psychology perspective for behavior and cognition assumptions."""

    name = "psychology"
    version = "0.1"

    def audit(
        self,
        artifact: dict[str, Any],
        local_context: dict[str, Any],
        unresolved_conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {
            "observations": ["behavioral assumptions rely on stable preference claims"],
            "criticisms": ["limited treatment of cognitive load effects"],
            "revisions": ["add bounded-rationality adjustment scenario"],
            "risks": ["survey framing may trigger demand characteristics"],
            "questions": ["what mechanisms reduce response fatigue bias?"],
            "evidence_needs": ["collect manipulation-check outcomes"],
            "confidence": 0.52,
        }
        return self._validated(payload)


MODULE_REGISTRY: dict[str, type[BasePerspectiveModule]] = {
    EconomicsModule.name: EconomicsModule,
    PhilosophyModule.name: PhilosophyModule,
    PsychologyModule.name: PsychologyModule,
}


def get_registered_module_class(name: str) -> type[BasePerspectiveModule] | None:
    """Return registered module class by normalized name."""

    return MODULE_REGISTRY.get(str(name).strip().lower())
