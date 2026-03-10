from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.governor import validate_precommit_action
from src.protocol import is_independent_critique, persona_diversity_score


def test_is_independent_critique_false_when_only_wording_differs():
    critique_a = {
        "evidence_refs": ["paper-1"],
        "attack_labels": ["identification-risk"],
        "challenged_fields": ["assumption_set"],
        "reasoning_path_labels": ["causal-chain"],
        "text": "这个识别策略很脆弱。",
    }
    critique_b = {
        "evidence_refs": ["paper-2"],
        "attack_labels": ["identification-risk"],
        "challenged_fields": ["assumption_set"],
        "reasoning_path_labels": ["causal-chain"],
        "text": "同样的问题：识别方案并不稳健。",
    }

    assert is_independent_critique(critique_a, critique_b) is False


def test_persona_diversity_score_higher_for_distinct_personas():
    low_diversity = {
        "agents": [
            {"human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"human_base_weight": 0.52, "module_weights": {"economics": 0.48}},
        ]
    }
    high_diversity = {
        "agents": [
            {"human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
        ]
    }

    assert persona_diversity_score(high_diversity) > persona_diversity_score(low_diversity)


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
