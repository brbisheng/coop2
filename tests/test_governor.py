from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.governor import validate_precommit_action


def test_validate_precommit_action_only_allows_park_or_continue_when_gate_fails():
    critiques = [
        {
            "attack_labels": ["identification-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
        {
            "attack_labels": ["identification-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
    ]
    panel_state = {
        "agents": [
            {"human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
        ]
    }

    ok_commit, _ = validate_precommit_action("commit", critiques, panel_state)
    ok_park, _ = validate_precommit_action("park", critiques, panel_state)

    assert ok_commit is False
    assert ok_park is True


def test_validate_precommit_action_fails_when_unique_agents_below_three():
    critiques = [
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
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
        ]
    }
    patches = [{"proposed_changes": {"mechanism": "updated"}}]

    ok, reason = validate_precommit_action(
        "commit",
        critiques,
        panel_state,
        accepted_patches=patches,
    )

    assert ok is False
    assert "unique_agents must be >= 3" in reason


def test_validate_precommit_action_fails_when_patch_has_no_field_changes():
    critiques = [
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
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }
    patches = [{"proposed_changes": {}}, {"note": "missing structured field changes"}]

    ok, reason = validate_precommit_action(
        "commit",
        critiques,
        panel_state,
        accepted_patches=patches,
    )

    assert ok is False
    assert "accepted patch must target explicit artifact fields" in reason


def test_validate_precommit_action_fails_when_unresolved_dissent_not_saved():
    critiques = [
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
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }
    patches = [{"proposed_changes": {"mechanism": "updated"}}]
    unresolved = [{"dissent_id": "d-1", "status": "open"}]

    ok, reason = validate_precommit_action(
        "commit",
        critiques,
        panel_state,
        accepted_patches=patches,
        unresolved_dissents=unresolved,
        unresolved_dissent_saved=False,
    )

    assert ok is False
    assert "unresolved dissent must be saved before commit" in reason


def test_validate_precommit_action_allows_commit_when_all_gates_pass():
    critiques = [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
            "evidence_refs": ["paper-1"],
        },
        {
            "attack_labels": ["measurement-risk"],
            "challenged_fields": ["outcome_vars"],
            "reasoning_path_labels": ["construct-validity"],
            "evidence_refs": ["dataset-2"],
        },
    ]
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }
    patches = [{"proposed_changes": {"mechanism": "updated", "outcome_vars": ["x"]}}]
    unresolved = [{"dissent_id": "d-1", "status": "open"}]

    ok, reason = validate_precommit_action(
        "commit",
        critiques,
        panel_state,
        accepted_patches=patches,
        unresolved_dissents=unresolved,
        unresolved_dissent_saved=True,
    )

    assert ok is True
    assert reason == "precommit checks passed"


def test_validate_precommit_action_fails_when_soul_overrides_governance_fields():
    critiques = [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
            "evidence_refs": ["paper-1"],
        },
        {
            "attack_labels": ["measurement-risk"],
            "challenged_fields": ["outcome_vars"],
            "reasoning_path_labels": ["construct-validity"],
            "evidence_refs": ["dataset-2"],
        },
    ]
    panel_state = {
        "agents": [
            {
                "agent_id": "a1",
                "human_base_weight": 0.5,
                "module_weights": {"economics": 0.5},
                "soul_profile": {"style": {"min_critiques": 1}},
            },
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }
    patches = [{"proposed_changes": {"mechanism": "updated", "outcome_vars": ["x"]}}]

    ok, reason = validate_precommit_action(
        "commit",
        critiques,
        panel_state,
        accepted_patches=patches,
        unresolved_dissents=[],
        unresolved_dissent_saved=True,
    )

    assert ok is False
    assert "soul profile cannot override commit rules/min critique constraints" in reason


def test_validate_precommit_action_fails_when_panel_soul_overrides_governance_fields():
    critiques = [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
            "evidence_refs": ["paper-1"],
        },
        {
            "attack_labels": ["measurement-risk"],
            "challenged_fields": ["outcome_vars"],
            "reasoning_path_labels": ["construct-validity"],
            "evidence_refs": ["dataset-2"],
        },
    ]
    panel_state = {
        "soul_profile": {"temperament": {"diversity_threshold": 0.0}},
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ],
    }
    patches = [{"proposed_changes": {"mechanism": "updated", "outcome_vars": ["x"]}}]

    ok, reason = validate_precommit_action(
        "commit",
        critiques,
        panel_state,
        accepted_patches=patches,
        unresolved_dissents=[],
        unresolved_dissent_saved=True,
    )

    assert ok is False
    assert "soul profile cannot override commit rules/min critique constraints" in reason
