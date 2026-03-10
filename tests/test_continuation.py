from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import build_continuation_pack


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_long_history_continuation_trim_keeps_unresolved_dissent(tmp_path: Path):
    session_dir = tmp_path / "session_001"
    dissent_dir = session_dir / "dissent"
    dissent_dir.mkdir(parents=True)

    snapshot = {
        "snapshot_id": "snap_009",
        "priority_open_issues": [
            {
                "issue_id": "iss-1",
                "artifact_id": "artifact_main_v3",
                "summary": "关键识别假设仍有冲突",
            }
        ],
        "next_recommended_arena": "policy",
        "artifact_lineages": {
            "artifact_main_v3": ["artifact_main_v1", "artifact_main_v2", "artifact_main_v3"]
        },
    }
    (session_dir / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    commits = [
        {"commit_id": f"c-{idx}", "artifact_id": "artifact_other", "status": "applied"}
        for idx in range(40)
    ]
    commits += [
        {"commit_id": "c-lineage-1", "artifact_id": "artifact_main_v2", "status": "applied"},
        {"commit_id": "c-lineage-2", "artifact_id": "artifact_main_v3", "status": "pending"},
    ]
    _write_jsonl(session_dir / "commits.jsonl", commits)

    events = [
        {"event_id": f"e-{idx}", "artifact_id": "artifact_main_v3", "type": "discussion"}
        for idx in range(30)
    ] + [
        {"event_id": "e-other", "artifact_id": "artifact_other", "type": "discussion"}
    ]
    _write_jsonl(session_dir / "event_log.jsonl", events)

    # unresolved dissent is intentionally old and should survive budget trimming.
    unresolved = {
        "dissent_id": "d-important",
        "artifact_id": "artifact_main_v1",
        "status": "open",
        "message": "旧分歧节点但仍未解决",
    }
    resolved = {
        "dissent_id": "d-resolved",
        "artifact_id": "artifact_main_v3",
        "status": "resolved",
        "resolved": True,
        "message": "已解决",
    }
    other = {
        "dissent_id": "d-other",
        "artifact_id": "artifact_other",
        "status": "open",
        "message": "不相关 lineage",
    }
    for card in (unresolved, resolved, other):
        (dissent_dir / f"{card['dissent_id']}.json").write_text(
            json.dumps(card, ensure_ascii=False), encoding="utf-8"
        )

    pack = build_continuation_pack(
        session_dir,
        goal="resolve_specific_conflict",
        target_artifact_id="artifact_main_v3",
        recent_k=3,
        entry_budget=6,
    )

    assert pack.goal == "resolve_specific_conflict"
    assert pack.arena == "policy"
    assert pack.minimal_context["priority_open_issues"][0]["issue_id"] == "iss-1"

    loaded_dissent_ids = {item["dissent_id"] for item in pack.minimal_context["dissents"]}
    assert "d-important" in loaded_dissent_ids
    assert "d-other" not in loaded_dissent_ids

    unresolved_ids = {item["dissent_id"] for item in pack.unresolved_conflicts}
    assert "d-important" in unresolved_ids
