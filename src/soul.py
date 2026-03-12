"""Soul profile provider contract and validation primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .protocol import soul_overrides_governance


class SoulValidationError(ValueError):
    """Raised when a soul payload violates the allowed schema."""


class SoulProvider(Protocol):
    """Provider that resolves soul payloads by ``agent_id``."""

    def get_soul_profile(self, agent_id: str) -> dict[str, Any] | None:
        """Return soul payload for the provided agent id."""


ALLOWED_SOUL_FIELDS = {"style", "temperament"}


@dataclass(slots=True)
class SoulProfile:
    """Validated soul profile constrained to stylistic knobs only."""

    style: dict[str, Any] = field(default_factory=dict)
    temperament: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.style, dict):
            raise SoulValidationError("soul.style must be a mapping")
        if not isinstance(self.temperament, dict):
            raise SoulValidationError("soul.temperament must be a mapping")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.style:
            payload["style"] = dict(self.style)
        if self.temperament:
            payload["temperament"] = dict(self.temperament)
        return payload


def validate_soul_profile(raw: dict[str, Any] | None) -> SoulProfile:
    """Validate a raw soul payload and return a normalized profile."""

    if raw is None:
        return SoulProfile()
    if not isinstance(raw, dict):
        raise SoulValidationError("soul profile must be a mapping")

    unknown = sorted(key for key in raw if key not in ALLOWED_SOUL_FIELDS)
    if unknown:
        raise SoulValidationError(
            "soul profile may only set style/temperament fields; "
            f"rejected keys: {unknown}"
        )

    profile = SoulProfile(
        style=dict(raw.get("style", {})),
        temperament=dict(raw.get("temperament", {})),
    )

    if soul_overrides_governance(profile.to_dict()):
        raise SoulValidationError(
            "soul profile cannot override commit rules/min critique constraints"
        )

    return profile


def validate_soul_payload(raw: dict[str, Any] | None) -> SoulProfile:
    """Backward-compatible alias for soul validation."""

    return validate_soul_profile(raw)


def strip_soul_fields_for_governance(panel_state: dict[str, Any]) -> dict[str, Any]:
    """Return governance-ready panel state with soul fields removed."""

    normalized = dict(panel_state)
    normalized.pop("soul_profile", None)

    raw_agents = normalized.get("agents")
    if isinstance(raw_agents, list):
        clean_agents: list[dict[str, Any]] = []
        for agent in raw_agents:
            if not isinstance(agent, dict):
                continue
            clean_agent = dict(agent)
            clean_agent.pop("soul_profile", None)
            clean_agents.append(clean_agent)
        normalized["agents"] = clean_agents

    return normalized
