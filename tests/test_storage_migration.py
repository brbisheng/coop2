from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import build_continuation_pack, load_artifact_version, run_micro_deliberation
from src.storage import ensure_current_schema


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_ensure_current_schema_migrates_legacy_decision_and_arena():
    migrated = ensure_current_schema(
        {
            "schema_version": 1,
            "decision": "commit",
            "requested_action": "commit",
            "arena": "policy",
            "status": "archived",
        }
    )

    assert migrated["schema_version"] == 3
    assert migrated["decision"] == "accept"
    assert migrated["requested_action"] == "accept"
    assert migrated["arena"] == "empirical_grounding"
    assert migrated["status"] == "park"


def test_ensure_current_schema_migrates_legacy_status_variants():
    for old_status, expected in {
        "active": "accept",
        "accepted": "accept",
        "branched": "branch",
        "parked": "park",
        "rejected": "reject",
    }.items():
        migrated = ensure_current_schema({"schema_version": 1, "status": old_status})
        assert migrated["status"] == expected


def test_engine_can_read_migrated_legacy_records(tmp_path: Path):
    session_dir = tmp_path / "legacy_session"
    session_dir.mkdir(parents=True)

    snapshot = {
        "schema_version": 1,
        "snapshot_id": "snap_legacy",
        "priority_open_issues": [
            {"issue_id": "iss-1", "artifact_id": "artifact_main_v3", "summary": "legacy"}
        ],
        "next_recommended_arena": "policy",
        "artifact_lineages": {"artifact_main_v3": ["artifact_main_v2", "artifact_main_v3"]},
    }
    (session_dir / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    _write_jsonl(
        session_dir / "commits.jsonl",
        [
            {
                "schema_version": 1,
                "commit_id": "c-1",
                "artifact_id": "artifact_main_v3",
                "decision": "commit",
                "status": "applied",
            }
        ],
    )
    _write_jsonl(
        session_dir / "event_log.jsonl",
        [
            {
                "schema_version": 1,
                "event_id": "e-1",
                "artifact_id": "artifact_main_v3",
                "arena": "policy",
                "type": "micro_deliberation_round",
            }
        ],
    )

    pack = build_continuation_pack(
        session_dir,
        goal="resume",
        target_artifact_id="artifact_main_v3",
    )

    assert pack.arena == "empirical_grounding"
    assert pack.minimal_context["commits"][0]["decision"] == "accept"
    assert pack.minimal_context["events"][0]["arena"] == "empirical_grounding"


def test_version_replay_uses_snapshot_head_pointer(tmp_path: Path):
    session = tmp_path / "session_replay"
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

    run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "v1"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )
    run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "v2"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )

    latest = load_artifact_version(session, artifact_id="artifact_main")
    replay_v1 = load_artifact_version(session, artifact_id="artifact_main", version="v1")

    assert latest["version"] == "v2"
    assert latest["proposed_changes"] == [{"mechanism": "v2"}]
    assert replay_v1["version"] == "v1"
    assert replay_v1["proposed_changes"] == [{"mechanism": "v1"}]


def test_continuation_compatible_with_new_artifact_head_layout(tmp_path: Path):
    session_dir = tmp_path / "layout_v3"
    session_dir.mkdir(parents=True)

    snapshot = {
        "schema_version": 3,
        "snapshot_id": "snap_v3",
        "priority_open_issues": [{"issue_id": "iss-1", "artifact_id": "artifact_main_v2"}],
        "next_recommended_arena": "mechanism",
        "artifact_lineages": {"artifact_main": ["artifact_main_v1", "artifact_main_v2"]},
        "artifact_heads": {
            "artifact_main": {
                "artifact_id": "artifact_main_v2",
                "version": "v2",
                "path": "artifacts/artifact_main/v2.json",
            }
        },
    }
    (session_dir / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    _write_jsonl(
        session_dir / "commits.jsonl",
        [{"schema_version": 3, "commit_id": "c-2", "artifact_id": "artifact_main_v2", "status": "applied"}],
    )
    _write_jsonl(
        session_dir / "event_log.jsonl",
        [{"schema_version": 3, "event_id": "e-2", "artifact_id": "artifact_main_v2", "arena": "mechanism"}],
    )

    pack = build_continuation_pack(session_dir, goal="resume", target_artifact_id="artifact_main")
    assert pack.minimal_context["commits"][0]["artifact_id"] == "artifact_main_v2"
