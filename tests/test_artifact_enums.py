from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.artifacts import ArtifactCard, CommitRecord, DebateTurn, normalize_conflict_type
from src.protocol import ModelValidationError


_TRACEABILITY = {
    "parent_ids": ["artifact_main_v1"],
    "version": "v2",
    "open_issues": ["issue-1"],
    "proposed_changes": {"mechanism": "clarified"},
    "reasons": "picked mechanism patch for identifiability",
    "dissent_patch_ids": ["d-001"],
    "why_not_others": "alternative A lacks empirical support",
}




def test_artifact_card_missing_parent_ids_raises_validation_error():
    with pytest.raises(ModelValidationError, match="parent_ids is required"):
        ArtifactCard(
            artifact_id="a-1",
            title="title",
            content="content",
            status="accept",
            version="v1",
            open_issues=["issue-1"],
            proposed_changes={"mechanism": "clarified"},
            reasons="reason",
            dissent_patch_ids=["d-1"],
            why_not_others="alternative lacks support",
        )


def test_artifact_card_missing_why_not_others_raises_validation_error():
    with pytest.raises(ModelValidationError, match="why_not_others is required"):
        ArtifactCard(
            artifact_id="a-2",
            title="title",
            content="content",
            status="accept",
            parent_ids=["a-1"],
            version="v2",
            open_issues=["issue-1"],
            proposed_changes={"mechanism": "clarified"},
            reasons="reason",
            dissent_patch_ids=["d-1"],
        )
def test_artifact_status_rejects_invalid_value():
    with pytest.raises(ModelValidationError):
        ArtifactCard(
            artifact_id="idea_1",
            title="title",
            content="content",
            status="unknown_status",
            **_TRACEABILITY,
        )


def test_debate_turn_arena_rejects_invalid_value():
    with pytest.raises(ModelValidationError):
        DebateTurn(
            turn_id="turn_1",
            arena="invalid_arena",
            decision="accept",
            message="msg",
        )




def test_artifact_status_accepts_legacy_aliases():
    card = ArtifactCard(
        artifact_id="idea_legacy",
        title="title",
        content="content",
        status="parked",
        **_TRACEABILITY,
    )

    assert card.status.value == "park"


def test_debate_turn_accepts_legacy_aliases():
    turn = DebateTurn(
        turn_id="turn_legacy",
        arena="policy",
        decision="commit",
        message="msg",
    )

    assert turn.arena.value == "empirical_grounding"
    assert turn.decision.value == "accept"

def test_commit_record_missing_traceability_fields_raises_validation_error():
    with pytest.raises(ModelValidationError, match="parent_ids is required"):
        CommitRecord(
            commit_id="c-1",
            patch_ids=["p-1"],
            status="applied",
            version="v2",
            open_issues=["issue-1"],
            proposed_changes={"mechanism": "clarified"},
            reasons="good",
            dissent_patch_ids=["d-1"],
            why_not_others="other branch conflicts with constraints",
        )


def test_commit_record_requires_non_empty_explanation_fields():
    with pytest.raises(ModelValidationError, match="reasons must be a non-empty string"):
        CommitRecord(
            commit_id="c-2",
            patch_ids=["p-2"],
            status="applied",
            parent_ids=["c-1"],
            version="v2",
            open_issues=["issue-1"],
            proposed_changes={"mechanism": "clarified"},
            reasons="",
            dissent_patch_ids=["d-1"],
            why_not_others="",
        )


def test_conflict_type_rejects_invalid_value():
    with pytest.raises(ModelValidationError, match="Invalid value for 'conflict_type'"):
        normalize_conflict_type("unknown")


def test_conflict_type_accepts_allowed_values():
    assert normalize_conflict_type("Mechanism") == "mechanism"
