"""Governor checks for deliberation flow control."""

from __future__ import annotations

from typing import Any

from .protocol import (
    DEFAULT_PERSONA_DIVERSITY_THRESHOLD,
    is_independent_critique,
    persona_diversity_score,
)


def validate_precommit_action(
    proposed_action: str,
    critiques: list[dict[str, Any]],
    panel_state: dict[str, Any],
    diversity_threshold: float = DEFAULT_PERSONA_DIVERSITY_THRESHOLD,
    *,
    accepted_patches: list[dict[str, Any]] | None = None,
    unresolved_dissents: list[dict[str, Any]] | None = None,
    unresolved_dissent_saved: bool | None = None,
) -> tuple[bool, str]:
    """Validate pre-commit governance constraints.

    When quality gates fail, only `park` and continuing-discussion actions are permitted.
    """

    action = proposed_action.strip().lower()
    continue_like = {"continue", "continue_discussion", "discuss"}
    allowed_on_failure = {"park", *continue_like}

    independent = len(critiques) >= 2 and is_independent_critique(critiques[0], critiques[1])
    diversity = persona_diversity_score(panel_state)

    raw_agents = panel_state.get("agents", panel_state.get("panel", []))
    unique_ids: set[str] = set()
    if isinstance(raw_agents, list):
        for agent in raw_agents:
            if not isinstance(agent, dict):
                continue
            candidate = agent.get("agent_id") or agent.get("id") or agent.get("name")
            if isinstance(candidate, str) and candidate.strip():
                unique_ids.add(candidate.strip())
    unique_agents = len(unique_ids) if unique_ids else (len(raw_agents) if isinstance(raw_agents, list) else 0)

    patches = accepted_patches or []
    has_field_targeted_patch = any(
        isinstance(patch.get("proposed_changes"), dict) and bool(patch.get("proposed_changes"))
        for patch in patches
        if isinstance(patch, dict)
    )

    unresolved = unresolved_dissents or []
    dissent_gate_ok = (not unresolved) or (unresolved_dissent_saved is True)

    gates_passed = (
        unique_agents >= 3
        and independent
        and diversity >= diversity_threshold
        and has_field_targeted_patch
        and dissent_gate_ok
    )

    if gates_passed:
        return True, "precommit checks passed"

    if action in allowed_on_failure:
        return True, "quality gate not met; park/continue is allowed"

    reasons: list[str] = []
    if unique_agents < 3:
        reasons.append("unique_agents must be >= 3")
    if not independent:
        reasons.append("need >= 2 independent critiques")
    if diversity < diversity_threshold:
        reasons.append(f"panel persona diversity must be >= {diversity_threshold:.2f}")
    if not has_field_targeted_patch:
        reasons.append("accepted patch must target explicit artifact fields")
    if not dissent_gate_ok:
        reasons.append("unresolved dissent must be saved before commit")

    reason_text = "; ".join(reasons) if reasons else "precommit checks failed"
    return (False, f"{reason_text}; only park/continue_discussion allowed")
