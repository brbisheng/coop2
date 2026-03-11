from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import build_continuation_pack
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

    assert migrated["schema_version"] == 2
    assert migrated["decision"] == "accept"
    assert migrated["requested_action"] == "accept"
    assert migrated["arena"] == "empirical_grounding"
    assert migrated["status"] == "parked"


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
