from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src.engine import build_manuscript_draft_cards_from_records
from src.service_api import ServiceApiValidationError, export_manuscript, run_round


def _panel_state() -> dict:
    return {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }


def _critiques() -> list[dict]:
    return [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
        {
            "attack_labels": ["measurement-risk"],
            "challenged_fields": ["outcome_vars"],
            "reasoning_path_labels": ["construct-validity"],
        },
    ]


def test_build_manuscript_cards_keeps_references_complete():
    snapshot = {"snapshot_id": "snap_1", "latest_commits": ["c_1"]}
    commits = [
        {
            "commit_id": "c_1",
            "artifact_id": "artifact_main",
            "open_issues": ["issue_a"],
            "why_not_others": ["alt_a"],
        }
    ]
    dissents = [
        {
            "dissent_id": "d_1",
            "artifact_id": "artifact_main",
            "status": "open",
            "summary": "conflict_a",
        }
    ]

    cards = build_manuscript_draft_cards_from_records(
        snapshot=snapshot,
        commits=commits,
        dissents=dissents,
        artifact_id="artifact_main",
    )

    assert len(cards) == 1
    payload = cards[0].to_dict()
    assert payload["source_snapshot_id"] == "snap_1"
    assert payload["source_commit_id"] == "c_1"
    assert "commit:c_1" in payload["evidence_refs"]
    assert "dissent:d_1" in payload["evidence_refs"]
    assert "issue_a" in payload["pending_conflicts"]
    assert "conflict_a" in payload["pending_conflicts"]


def test_export_manuscript_api_returns_structured_skeleton(tmp_path: Path):
    session_dir = tmp_path / "session_manuscript"
    run_round(
        {
            "session_dir": str(session_dir),
            "artifact_id": "artifact_main",
            "arena": "mechanism",
            "proposed_action": "commit",
            "critiques": _critiques(),
            "panel_state": _panel_state(),
            "accepted_patches": [{"proposed_changes": {"mechanism": "clarified"}}],
            "unresolved_dissents": [
                {
                    "dissent_id": "dissent_1",
                    "artifact_id": "artifact_main",
                    "status": "open",
                    "message": "evidence threshold is weak",
                    "conflict_type": "evidence",
                    "why_not": "alternative mechanism not ruled out",
                }
            ],
            "unresolved_dissent_saved": True,
        }
    )

    payload = export_manuscript({"session_dir": str(session_dir), "artifact_id": "artifact_main"})

    assert payload["artifact_id"] == "artifact_main"
    assert payload["snapshot_id"]
    assert payload["manuscript_cards"]
    first_card = payload["manuscript_cards"][0]
    assert first_card["artifact_id"] == "artifact_main"
    assert first_card["evidence_refs"]
    assert first_card["pending_conflicts"]


def test_export_manuscript_requires_session_dir():
    with pytest.raises(ServiceApiValidationError):
        export_manuscript({"artifact_id": "artifact_main"})
