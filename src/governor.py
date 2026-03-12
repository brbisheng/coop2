"""Governor checks for deliberation flow control."""

from __future__ import annotations

from typing import Any

from .protocol import (
    DEFAULT_PERSONA_DIVERSITY_THRESHOLD,
    DebateDecision,
    is_independent_critique,
    persona_diversity_score,
    soul_overrides_governance,
)


def _anti_repetition_check(panel_state: dict[str, Any]) -> tuple[bool, str | None]:
    """Check if the same agent repeatedly holds critical seats over threshold."""

    cfg = panel_state.get("anti_repetition", {})
    if not isinstance(cfg, dict):
        return True, None

    enabled = bool(cfg.get("enabled", False))
    if not enabled:
        return True, None

    threshold = int(cfg.get("consecutive_threshold", 3))
    action = str(cfg.get("on_violation", "reject")).strip().lower()
    critical_seats = {
        str(item).strip().lower()
        for item in cfg.get("critical_seats", ["proposer", "critic"])
        if str(item).strip()
    }
    seat_history = panel_state.get("seat_history", [])
    if not isinstance(seat_history, list) or not critical_seats:
        return True, None

    streak = 0
    previous_agent: str | None = None
    for row in seat_history:
        if not isinstance(row, dict):
            continue
        seat = str(row.get("seat", "")).strip().lower()
        if seat not in critical_seats:
            continue
        agent_id = str(row.get("agent_id", "")).strip()
        if not agent_id:
            continue
        if agent_id == previous_agent:
            streak += 1
        else:
            previous_agent = agent_id
            streak = 1

    if streak < threshold:
        return True, None

    if action == "downweight":
        return True, "anti-repetition triggered: recommend downweight for repeated critical-seat owner"
    return False, "anti-repetition triggered: repeated critical-seat owner exceeds threshold"


def _seat_coverage_quality_check(panel_state: dict[str, Any]) -> tuple[bool, str | None]:
    """Check critical seat coverage quality to avoid long-term monopoly by one agent."""

    cfg = panel_state.get("seat_coverage_quality", {})
    if not isinstance(cfg, dict) or not bool(cfg.get("enabled", False)):
        return True, None

    action = str(cfg.get("on_violation", "reject")).strip().lower()
    critical_seats = {
        str(item).strip().lower()
        for item in cfg.get("critical_seats", ["proposer", "critic"])
        if str(item).strip()
    }
    window = int(cfg.get("window_size", 6))
    max_share = float(cfg.get("max_single_agent_share", 0.75))

    seat_history = panel_state.get("seat_history", [])
    if not isinstance(seat_history, list) or not critical_seats or window <= 0:
        return True, None

    recent_rows = [row for row in seat_history if isinstance(row, dict)][-window:]
    owner_counts: dict[str, int] = {}
    covered = 0
    for row in recent_rows:
        seat = str(row.get("seat", "")).strip().lower()
        if seat not in critical_seats:
            continue
        agent_id = str(row.get("agent_id", "")).strip()
        if not agent_id:
            continue
        covered += 1
        owner_counts[agent_id] = owner_counts.get(agent_id, 0) + 1

    if covered == 0 or not owner_counts:
        return True, None

    top_agent, top_count = max(owner_counts.items(), key=lambda item: item[1])
    share = top_count / covered
    if share <= max_share:
        return True, None

    msg = (
        "seat coverage quality check failed: "
        f"critical seats overly concentrated on {top_agent} ({share:.2f}>{max_share:.2f})"
    )
    if action == "downweight":
        return True, f"{msg}; recommend downweight"
    return False, msg


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
    allowed_on_failure = {DebateDecision.PARK.value, *continue_like}

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

    soul_policy_ok = not soul_overrides_governance(panel_state.get("soul_profile", {}))
    if soul_policy_ok and isinstance(raw_agents, list):
        for agent in raw_agents:
            if not isinstance(agent, dict):
                continue
            if soul_overrides_governance(agent.get("soul_profile", {})):
                soul_policy_ok = False
                break

    gates_passed = (
        unique_agents >= 3
        and independent
        and diversity >= diversity_threshold
        and has_field_targeted_patch
        and dissent_gate_ok
        and soul_policy_ok
    )

    anti_repeat_ok, anti_repeat_reason = _anti_repetition_check(panel_state)
    coverage_ok, coverage_reason = _seat_coverage_quality_check(panel_state)
    gates_passed = gates_passed and anti_repeat_ok and coverage_ok

    if gates_passed:
        notices = [item for item in [anti_repeat_reason, coverage_reason] if item]
        if notices:
            return True, f"precommit checks passed; {'; '.join(notices)}"
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
    if not soul_policy_ok:
        reasons.append("soul profile cannot override commit rules/min critique constraints")
    if anti_repeat_reason and not anti_repeat_ok:
        reasons.append(anti_repeat_reason)
    if coverage_reason and not coverage_ok:
        reasons.append(coverage_reason)

    reason_text = "; ".join(reasons) if reasons else "precommit checks failed"
    return (False, f"{reason_text}; only park/continue_discussion allowed")
