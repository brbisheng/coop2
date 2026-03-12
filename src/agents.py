"""Agent composition layer for HumanBase + perspectives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .human_base import HumanBaseProfile
from .perspectives import PerspectiveModule, get_registered_module_class
from .soul import SoulProvider, SoulValidationError, validate_soul_profile


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


def interpret_seat_policy(raw_policy: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize seat policy into explicit preference/forbidden/cooldown form."""

    policy = raw_policy if isinstance(raw_policy, dict) else {}

    preferred: list[str] = []
    if isinstance(policy.get("preferred_seat"), str):
        preferred.append(policy["preferred_seat"])
    if isinstance(policy.get("preferred_seats"), list):
        preferred.extend(item for item in policy["preferred_seats"] if isinstance(item, str))

    forbidden: list[str] = []
    if isinstance(policy.get("forbidden_seat"), str):
        forbidden.append(policy["forbidden_seat"])
    if isinstance(policy.get("forbidden_seats"), list):
        forbidden.extend(item for item in policy["forbidden_seats"] if isinstance(item, str))

    cooldown_raw = policy.get("cooldown_rounds", 0)
    cooldown = int(cooldown_raw) if isinstance(cooldown_raw, (int, float)) else 0
    cooldown = max(cooldown, 0)

    return {
        "preferred_seats": sorted({item.strip().lower() for item in preferred if item.strip()}),
        "forbidden_seats": sorted({item.strip().lower() for item in forbidden if item.strip()}),
        "cooldown_rounds": cooldown,
    }


def seat_policy_allows_seat(
    seat_policy: dict[str, Any],
    *,
    seat: str,
    current_round: int,
    last_assigned_round: int | None,
) -> bool:
    """Check whether a seat policy allows assigning `seat` in current round."""

    normalized = interpret_seat_policy(seat_policy)
    seat_name = seat.strip().lower()
    if seat_name in normalized["forbidden_seats"]:
        return False

    cooldown_rounds = int(normalized["cooldown_rounds"])
    if last_assigned_round is not None and cooldown_rounds > 0:
        if current_round - int(last_assigned_round) <= cooldown_rounds:
            return False
    return True


def _normalize_weights(weights: dict[str, Any]) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    for key, value in weights.items():
        if isinstance(value, (int, float)) and value > 0:
            cleaned[str(key).strip().lower()] = float(value)

    total = sum(cleaned.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in cleaned.items()}


def _instantiate_modules(module_weights: dict[str, float]) -> list[PerspectiveModule]:
    if not module_weights:
        module_cls = get_registered_module_class("economics")
        if module_cls is None:
            raise AgentConfigError("default perspective module 'economics' is not registered")
        return [module_cls()]

    modules: list[PerspectiveModule] = []
    missing: list[str] = []
    for module_name in module_weights:
        module_cls = get_registered_module_class(module_name)
        if module_cls is None:
            missing.append(module_name)
            continue
        modules.append(module_cls())

    if missing:
        raise AgentConfigError(f"unknown perspective module(s): {missing}")

    return modules


def build_agent_from_config(
    raw: dict[str, Any],
    soul_provider: SoulProvider | None = None,
) -> AgentInstance:
    """Build an AgentInstance from config mapping.

    HumanBase is mandatory by design.
    """

    agent_id = str(raw.get("agent_id", "")).strip()
    if not agent_id:
        raise AgentConfigError("agent_id is required")

    human_raw = raw.get("human_base")
    if not isinstance(human_raw, dict):
        raise AgentConfigError("human_base is required and must be a mapping")

    raw_weight = human_raw.get("weight", 0)
    raw_subvalves = human_raw.get("subvalves")

    if isinstance(raw_weight, dict):
        subvalves = dict(raw_weight)
        positive = [float(value) for value in subvalves.values() if isinstance(value, (int, float)) and value > 0]
        weight = sum(positive) / len(positive) if positive else 0.0
    else:
        subvalves = dict(raw_subvalves) if isinstance(raw_subvalves, dict) else {}
        weight = raw_weight

    human_base = HumanBaseProfile(
        weight=weight,
        subvalves=subvalves,
        heuristics=list(human_raw.get("heuristics", [])),
    )

    module_weights = _normalize_weights(raw.get("module_weights", {}))
    modules = _instantiate_modules(module_weights)

    base_soul_raw = raw.get("soul_profile")
    provided_soul_raw = soul_provider.get_soul_profile(agent_id) if soul_provider else None

    try:
        base_soul = validate_soul_profile(base_soul_raw if isinstance(base_soul_raw, dict) else None)
        provided_soul = validate_soul_profile(provided_soul_raw)
    except SoulValidationError as exc:
        raise AgentConfigError(str(exc)) from exc

    merged_soul = base_soul.to_dict()
    merged_soul.update(provided_soul.to_dict())

    return AgentInstance(
        agent_id=agent_id,
        human_base=human_base,
        perspective_modules=modules,
        seat_policy=interpret_seat_policy(dict(raw.get("seat_policy", {}))),
        memory_view=dict(raw.get("memory_view", {})),
        soul_profile=merged_soul,
        module_weights=module_weights,
    )


def persona_mix(agent: AgentInstance) -> dict[str, float]:
    """Return normalized human/module mix used by panel diversity logic."""

    mix = {"human_base": agent.human_base.weight}
    mix.update({f"human_base.{name}": value for name, value in agent.human_base.subvalves.items()})
    mix.update(agent.module_weights)

    total = sum(value for value in mix.values() if value > 0)
    if total <= 0:
        return {}

    return {key: value / total for key, value in mix.items() if value > 0}
