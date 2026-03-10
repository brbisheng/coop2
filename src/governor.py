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
) -> tuple[bool, str]:
    """Validate pre-commit governance constraints.

    When quality gates fail, only `park` and continuing-discussion actions are permitted.
    """

    action = proposed_action.strip().lower()
    continue_like = {"continue", "continue_discussion", "discuss"}
    allowed_on_failure = {"park", *continue_like}

    independent = len(critiques) >= 2 and is_independent_critique(critiques[0], critiques[1])
    diversity = persona_diversity_score(panel_state)
    gates_passed = independent and diversity >= diversity_threshold

    if gates_passed:
        return True, "precommit checks passed"

    if action in allowed_on_failure:
        return True, "quality gate not met; park/continue is allowed"

    return (
        False,
        "precommit checks failed: critiques must be independent and panel persona diversity "
        f"must be >= {diversity_threshold:.2f}; only park/continue_discussion allowed",
    )
