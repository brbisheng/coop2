"""Protocol-layer primitives for unified deliberation data models."""

from __future__ import annotations

from enum import Enum
from itertools import combinations
from math import sqrt
from typing import Any


CURRENT_SCHEMA_VERSION = 2
DEFAULT_PERSONA_DIVERSITY_THRESHOLD = 0.25


class ModelValidationError(ValueError):
    """Raised when a record does not satisfy model constraints."""


class ArtifactStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    BRANCHED = "branched"
    PARKED = "parked"
    ACCEPTED = "accepted"


class DebateDecision(str, Enum):
    ACCEPT = "accept"
    BRANCH = "branch"
    PARK = "park"
    REJECT = "reject"


class DebateArena(str, Enum):
    PROBLEM_FRAMING = "problem_framing"
    MECHANISM = "mechanism"
    EMPIRICAL_GROUNDING = "empirical_grounding"


class CommitStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    REVERTED = "reverted"


ENUM_COMPAT_ALIASES: dict[type[Enum], dict[str, str]] = {
    ArtifactStatus: {
        "archived": ArtifactStatus.PARKED.value,
    },
    DebateDecision: {
        "commit": DebateDecision.ACCEPT.value,
        "defer": DebateDecision.PARK.value,
    },
    DebateArena: {
        "general": DebateArena.PROBLEM_FRAMING.value,
        "code": DebateArena.MECHANISM.value,
        "policy": DebateArena.EMPIRICAL_GROUNDING.value,
    },
}


def parse_enum(raw_value: str, enum_type: type[Enum], field_name: str) -> Enum:
    """Parse/validate enum values with a clear error message."""
    normalized = str(raw_value).strip().lower()
    normalized = ENUM_COMPAT_ALIASES.get(enum_type, {}).get(normalized, normalized)
    try:
        return enum_type(normalized)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ModelValidationError(
            f"Invalid value for '{field_name}': {raw_value!r}. Allowed: {allowed}."
        ) from exc


def _as_tag_set(payload: dict[str, Any], keys: tuple[str, ...]) -> set[str]:
    values: set[str] = set()
    for key in keys:
        raw = payload.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            raw_items = [raw]
        elif isinstance(raw, (list, tuple, set)):
            raw_items = list(raw)
        else:
            continue
        values.update(str(item).strip().lower() for item in raw_items if str(item).strip())
    return values


def _overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def is_independent_critique(critique_a: dict[str, Any], critique_b: dict[str, Any]) -> bool:
    """Judge whether two critiques are meaningfully independent.

    Independence is evaluated by four axes:
    1) cited evidence,
    2) attack-point labels,
    3) challenged fields,
    4) reasoning-path labels.

    If attack labels and challenged fields are both highly overlapping, the critiques are treated
    as non-independent even when wording differs.
    """

    dimensions = {
        "evidence": (
            _as_tag_set(critique_a, ("evidence_refs", "evidence", "citations")),
            _as_tag_set(critique_b, ("evidence_refs", "evidence", "citations")),
        ),
        "attack": (
            _as_tag_set(critique_a, ("attack_labels", "attack_points", "labels")),
            _as_tag_set(critique_b, ("attack_labels", "attack_points", "labels")),
        ),
        "challenged": (
            _as_tag_set(critique_a, ("challenged_fields", "target_fields", "fields")),
            _as_tag_set(critique_b, ("challenged_fields", "target_fields", "fields")),
        ),
        "reasoning": (
            _as_tag_set(critique_a, ("reasoning_path_labels", "reasoning_tags", "path_tags")),
            _as_tag_set(critique_b, ("reasoning_path_labels", "reasoning_tags", "path_tags")),
        ),
    }

    populated = {
        name: _overlap_ratio(left, right)
        for name, (left, right) in dimensions.items()
        if left or right
    }
    if not populated:
        return False

    attack_overlap = populated.get("attack", 1.0)
    challenged_overlap = populated.get("challenged", 1.0)
    if attack_overlap >= 0.6 and challenged_overlap >= 0.6:
        return False

    low_overlap_dims = sum(1 for ratio in populated.values() if ratio < 0.4)
    avg_overlap = sum(populated.values()) / len(populated)
    return low_overlap_dims >= 2 and avg_overlap <= 0.45


def _agent_weight_vector(agent_state: dict[str, Any]) -> dict[str, float]:
    vector: dict[str, float] = {}

    human_weight = agent_state.get("human_base_weight", agent_state.get("human_weight", 0.0))
    if isinstance(human_weight, (int, float)) and human_weight > 0:
        vector["human_base"] = float(human_weight)

    raw_modules = agent_state.get("module_weights", {})
    if isinstance(raw_modules, dict):
        for module_name, raw_weight in raw_modules.items():
            if isinstance(raw_weight, (int, float)) and raw_weight > 0:
                vector[str(module_name).strip().lower()] = float(raw_weight)

    total = sum(vector.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in vector.items()}


def _euclidean_distance(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    keys = set(vec_a) | set(vec_b)
    return sqrt(sum((vec_a.get(key, 0.0) - vec_b.get(key, 0.0)) ** 2 for key in keys))


def persona_diversity_score(panel_state: dict[str, Any]) -> float:
    """Return a normalized [0,1] diversity score from HumanBase/module weight vectors."""

    raw_agents = panel_state.get("agents", panel_state.get("panel", []))
    if not isinstance(raw_agents, list):
        return 0.0

    vectors = [_agent_weight_vector(agent) for agent in raw_agents if isinstance(agent, dict)]
    vectors = [vector for vector in vectors if vector]
    if len(vectors) < 2:
        return 0.0

    distances = [_euclidean_distance(a, b) / sqrt(2) for a, b in combinations(vectors, 2)]
    if not distances:
        return 0.0
    return sum(distances) / len(distances)
