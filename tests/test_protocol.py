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



def test_persona_diversity_includes_human_subvalves():
    low_diversity = {
        "agents": [
            {
                "human_base_weight": 0.5,
                "human_base_subvalves": {
                    "practical_friction": 0.5,
                    "social_interpretation": 0.5,
                },
                "module_weights": {"economics": 0.5},
            },
            {
                "human_base_weight": 0.5,
                "human_base_subvalves": {
                    "practical_friction": 0.5,
                    "social_interpretation": 0.5,
                },
                "module_weights": {"economics": 0.5},
            },
        ]
    }
    high_diversity = {
        "agents": [
            {
                "human_base_weight": 0.5,
                "human_base_subvalves": {
                    "practical_friction": 0.9,
                    "social_interpretation": 0.1,
                },
                "module_weights": {"economics": 0.5},
            },
            {
                "human_base_weight": 0.5,
                "human_base_subvalves": {
                    "practical_friction": 0.1,
                    "social_interpretation": 0.9,
                },
                "module_weights": {"economics": 0.5},
            },
        ]
    }

    assert persona_diversity_score(high_diversity) > persona_diversity_score(low_diversity)
