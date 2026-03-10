"""Agent composition layer for HumanBase + perspectives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .human_base import HumanBaseProfile
from .perspectives import EconomicsModuleStub, PerspectiveModule


class AgentConfigError(ValueError):
    """Raised when agent config is invalid."""


@dataclass(slots=True)
class AgentInstance:
    agent_id: str
    human_base: HumanBaseProfile
    perspective_modules: list[PerspectiveModule]
    seat_policy: dict[str, Any] = field(default_factory=dict)
    memory_view: dict[str, Any] = field(default_factory=dict)
    soul_profile: dict[str, Any] = field(default_factory=dict)
    module_weights: dict[str, float] = field(default_factory=dict)


def _normalize_weights(weights: dict[str, Any]) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    for key, value in weights.items():
        if isinstance(value, (int, float)) and value > 0:
            cleaned[str(key)] = float(value)

    total = sum(cleaned.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in cleaned.items()}


def build_agent_from_config(raw: dict[str, Any]) -> AgentInstance:
    """Build an AgentInstance from config mapping.

    HumanBase is mandatory by design.
    """

    agent_id = str(raw.get("agent_id", "")).strip()
    if not agent_id:
        raise AgentConfigError("agent_id is required")

    human_raw = raw.get("human_base")
    if not isinstance(human_raw, dict):
        raise AgentConfigError("human_base is required and must be a mapping")

    human_base = HumanBaseProfile(
        weight=human_raw.get("weight", 0),
        heuristics=list(human_raw.get("heuristics", [])),
    )

    modules = [EconomicsModuleStub()]
    module_weights = _normalize_weights(raw.get("module_weights", {}))

    return AgentInstance(
        agent_id=agent_id,
        human_base=human_base,
        perspective_modules=modules,
        seat_policy=dict(raw.get("seat_policy", {})),
        memory_view=dict(raw.get("memory_view", {})),
        soul_profile=dict(raw.get("soul_profile", {})),
        module_weights=module_weights,
    )


def persona_mix(agent: AgentInstance) -> dict[str, float]:
    """Return normalized human/module mix used by panel diversity logic."""

    mix = {"human_base": agent.human_base.weight}
    mix.update(agent.module_weights)

    total = sum(value for value in mix.values() if value > 0)
    if total <= 0:
        return {}

    return {key: value / total for key, value in mix.items() if value > 0}
