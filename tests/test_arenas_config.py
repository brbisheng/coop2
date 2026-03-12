from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.arenas import ArenaConfigError, load_arenas


def test_load_arenas_from_config():
    specs = load_arenas("config/arenas.yaml")
    assert set(specs.keys()) == {
        "problem_framing",
        "counterexample_search",
        "mechanism",
        "empirical_grounding",
        "decision",
        "writing_prep",
    }
    mechanism = specs["mechanism"]
    assert mechanism.seat_allocation["history_penalty"] > 0
    assert mechanism.anti_repetition["enabled"] is True


def test_load_arenas_rejects_low_independent_critiques(tmp_path: Path):
    bad = {
        "arenas": [
            {
                "arena_name": "bad_arena",
                "accepted_artifact_types": ["research_idea"],
                "required_obligations": {
                    "propose": 1,
                    "independent_critiques": 1,
                    "repair_or_merge": 1,
                },
                "min_unique_agents": 3,
                "allowed_outputs": ["patch"],
            }
        ]
    }
    path = tmp_path / "bad_arenas.yaml"
    path.write_text(json.dumps(bad), encoding="utf-8")

    try:
        load_arenas(path)
    except ArenaConfigError:
        pass
    else:
        raise AssertionError("expected ArenaConfigError when independent_critiques < 2")


def test_new_arenas_have_required_structural_fields():
    specs = load_arenas("config/arenas.yaml")

    for arena_name in ("counterexample_search", "decision", "writing_prep"):
        spec = specs[arena_name]
        assert spec.required_obligations["propose"] == 1
        assert spec.required_obligations["independent_critiques"] >= 2
        assert spec.required_obligations["repair_or_merge"] == 1
        assert spec.required_obligations["decision"] == 1
        assert set(spec.allowed_outputs) == {"patch", "dissent", "merge"}
        assert spec.seat_allocation["history_penalty"] > 0
        assert spec.anti_repetition["enabled"] is True
