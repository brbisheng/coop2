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
    "evidence_refs",
    "evidence_type",
    "evidence_gap",
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

    list_fields = (
        "observations",
        "criticisms",
        "revisions",
        "risks",
        "questions",
        "evidence_needs",
        "evidence_refs",
    )
    for field in list_fields:
        if not isinstance(payload[field], list):
            raise PerspectiveValidationError(f"{field} must be a list")
        if any(not isinstance(item, str) or not item.strip() for item in payload[field]):
            raise PerspectiveValidationError(f"{field} entries must be non-empty strings")

    if not isinstance(payload["evidence_type"], str) or not payload["evidence_type"].strip():
        raise PerspectiveValidationError("evidence_type must be a non-empty string")

    if not isinstance(payload["evidence_gap"], str):
        raise PerspectiveValidationError("evidence_gap must be a string")

    evidence_refs = payload["evidence_refs"]
    evidence_type = payload["evidence_type"].strip().lower()
    evidence_gap = payload["evidence_gap"].strip()

    if evidence_type != "none" and not evidence_refs and not evidence_gap:
        raise PerspectiveValidationError(
            "minimal evidence completeness failed: provide evidence_refs or explain evidence_gap"
        )
    if evidence_type == "none" and not evidence_gap:
        raise PerspectiveValidationError(
            "minimal evidence completeness failed: evidence_gap is required when evidence_type is none"
        )

    if any("fake" in ref.lower() for ref in evidence_refs):
        raise PerspectiveValidationError("evidence_refs contains invalid fake evidence")

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
            "evidence_refs": ["doi:10.1000/example-econ-01"],
            "evidence_type": "empirical",
            "evidence_gap": "",
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
            "evidence_refs": ["doi:10.1000/example-phil-01"],
            "evidence_type": "theoretical",
            "evidence_gap": "",
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
            "evidence_refs": ["doi:10.1000/example-psy-01"],
            "evidence_type": "empirical",
            "evidence_gap": "",
            "confidence": 0.52,
        }
        return self._validated(payload)


MODULE_REGISTRY: dict[str, type[BasePerspectiveModule]] = {}


def register_perspective_module(module_cls: type[BasePerspectiveModule]) -> None:
    """Register a perspective module implementation by its declared name."""

    module_name = str(getattr(module_cls, "name", "")).strip().lower()
    if not module_name:
        raise PerspectiveValidationError("module class must declare non-empty name")
    MODULE_REGISTRY[module_name] = module_cls


def list_registered_modules() -> list[str]:
    """Return sorted module names for inspection/testing."""

    return sorted(MODULE_REGISTRY)


def get_registered_module_class(name: str) -> type[BasePerspectiveModule] | None:
    """Return registered module class by normalized name."""

    return MODULE_REGISTRY.get(str(name).strip().lower())


for _module in (EconomicsModule, PhilosophyModule, PsychologyModule):
    register_perspective_module(_module)
