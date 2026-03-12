from pathlib import Path
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.service_api import ServiceApiValidationError, build_continuation, read_artifact, run_round


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


def test_run_round_contract_missing_required_field(tmp_path: Path):
    payload = {
        "session_dir": str(tmp_path / "session_api_1"),
        "artifact_id": "artifact_main",
        "arena": "mechanism",
        "proposed_action": "commit",
        "critiques": _critiques(),
    }

    with pytest.raises(ServiceApiValidationError) as exc:
        run_round(payload)

    assert "missing required fields" in str(exc.value)
    assert "panel_state" in str(exc.value)


def test_run_round_contract_rejects_invalid_soul_profile(tmp_path: Path):
    payload = {
        "session_dir": str(tmp_path / "session_api_2"),
        "artifact_id": "artifact_main",
        "arena": "mechanism",
        "proposed_action": "commit",
        "critiques": _critiques(),
        "panel_state": _panel_state(),
        "soul_profile": {"min_critiques": 1, "style": {"tone": "hard"}},
    }

    with pytest.raises(ServiceApiValidationError) as exc:
        run_round(payload)

    assert "style/temperament" in str(exc.value)


def test_run_round_contract_rejects_invalid_arena(tmp_path: Path):
    payload = {
        "session_dir": str(tmp_path / "session_api_3"),
        "artifact_id": "artifact_main",
        "arena": "not_a_real_arena",
        "proposed_action": "commit",
        "critiques": _critiques(),
        "panel_state": _panel_state(),
    }

    with pytest.raises(ServiceApiValidationError) as exc:
        run_round(payload)

    assert "Invalid value for 'arena'" in str(exc.value)


def test_api_facade_round_continuation_and_artifact_read(tmp_path: Path):
    session_dir = tmp_path / "session_api_4"

    round_result = run_round(
        {
            "session_dir": str(session_dir),
            "artifact_id": "artifact_main",
            "arena": "mechanism",
            "proposed_action": "commit",
            "critiques": _critiques(),
            "panel_state": _panel_state(),
            "accepted_patches": [{"proposed_changes": {"mechanism": "clarified"}}],
            "soul_profile": {"style": {"tone": "concise"}},
        }
    )

    assert round_result["commit"]["artifact_id"] == "artifact_main"
    assert round_result["soul_profile"] == {"style": {"tone": "concise"}}

    continuation_payload = build_continuation(
        {
            "session_dir": str(session_dir),
            "goal": "resume",
            "target_artifact_id": "artifact_main",
        }
    )

    assert continuation_payload["goal"] == "resume"
    assert continuation_payload["target_artifact_id"] == "artifact_main"

    artifact_payload = read_artifact({"session_dir": str(session_dir), "artifact_id": "artifact_main"})
    assert artifact_payload["artifact_id"] == "artifact_main"
    assert artifact_payload["version"] == "v1"


def test_run_round_routes_soul_only_to_soul_ledger_not_governance(tmp_path: Path):
    session_dir = tmp_path / "session_api_dual_ledger"

    result = run_round(
        {
            "session_dir": str(session_dir),
            "artifact_id": "artifact_main",
            "arena": "mechanism",
            "proposed_action": "commit",
            "critiques": _critiques(),
            "panel_state": {
                **_panel_state(),
                "soul_profile": {"style": {"min_critiques": 999}},
                "agents": [
                    {
                        **_panel_state()["agents"][0],
                        "soul_profile": {"temperament": {"diversity_threshold": 0.0}},
                    },
                    *_panel_state()["agents"][1:],
                ],
            },
            "soul_profile": {"style": {"tone": "calm"}},
            "accepted_patches": [{"proposed_changes": {"mechanism": "clarified"}}],
        }
    )

    assert result["commit"]["allowed"] is True
    event = result["event"]
    assert event["cognitive_output_ref"].startswith("ledgers/cognitive/")
    assert event["soul_trace_ref"].startswith("ledgers/soul/")
    soul_trace = json.loads((session_dir / event["soul_trace_ref"]).read_text(encoding="utf-8"))
    assert soul_trace["soul_profile"] == {"style": {"tone": "calm"}}
