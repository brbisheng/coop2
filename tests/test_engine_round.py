from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import run_micro_deliberation, run_perspective_audit_batch


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def test_run_micro_round_produces_commit_event_and_snapshot(tmp_path: Path):
    session = tmp_path / "session_001"

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

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v3",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "clarified"}}],
        unresolved_dissents=[
            {
                "dissent_id": "d-1",
                "artifact_id": "artifact_main_v2",
                "status": "open",
                "message": "identification assumption unresolved",
                "why_not": "branch-B removed key mechanism variable",
            }
        ],
        unresolved_dissent_saved=True,
    )

    assert result["commit"]["allowed"] is True
    assert result["commit"]["decision"] == "accept"

    commits = _read_jsonl(session / "commits.jsonl")
    events = _read_jsonl(session / "event_log.jsonl")
    snapshot = json.loads((session / "snapshot.json").read_text(encoding="utf-8"))

    assert len(commits) == 1
    assert len(events) == 1
    assert commits[0]["commit_id"] in snapshot["latest_commits"]
    assert commits[0]["proposed_changes"] == [{"mechanism": "clarified"}]
    assert commits[0]["reasons"]
    assert commits[0]["why_not_others"]
    assert (session / "dissent" / "d-1.json").exists()


def test_run_micro_round_rejects_commit_when_invariants_fail(tmp_path: Path):
    session = tmp_path / "session_002"

    critiques = [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
    ]
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
        ]
    }

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v3",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "clarified"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )

    assert result["commit"]["allowed"] is False
    assert result["commit"]["decision"] == "park"
    assert "only park/continue_discussion allowed" in result["commit"]["reason"]


def test_lineage_chain_can_be_reconstructed_from_parent_ids(tmp_path: Path):
    session = tmp_path / "session_003"
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
            {"agent_id": "a1", "human_base_weight": 0.4, "module_weights": {"economics": 0.6}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
        ]
    }

    first = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v3",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "v1"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )
    second = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v3",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "v2"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )

    assert second["commit"]["parent_ids"] == [first["commit"]["commit_id"]]
    assert second["commit"]["version"] == "v2"



def test_run_perspective_audit_batch_with_multiple_modules_is_structured(tmp_path: Path):
    from src.perspectives import EconomicsModule, PsychologyModule

    audits = run_perspective_audit_batch(
        modules=[EconomicsModule(), PsychologyModule()],
        artifact={"artifact_id": "a1"},
        local_context={"arena": "mechanism"},
        unresolved_conflicts=[],
    )

    assert len(audits) == 2
    assert {item["module"] for item in audits} == {"economics", "psychology"}
    for item in audits:
        assert "audit" in item
        assert isinstance(item["audit"]["confidence"], (int, float))

    session = tmp_path / "session_004"
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
            {"agent_id": "a1", "human_base_weight": 0.4, "module_weights": {"economics": 0.6}},
            {"agent_id": "a2", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v4",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "audit-informed"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
        perspective_audits=audits,
    )

    assert result["event"]["perspective_audits"]
    assert result["event"]["audit_summary"]["module_count"] == 2
    assert "modules=economics,psychology" in result["event"]["patch_rationale"]
