"""Continuation orchestration for session-level retrieval."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .governor import validate_precommit_action
from .memory import ContinuationPack, build_minimal_context
from .protocol import DebateArena, parse_enum
from .storage import ensure_current_schema


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            if isinstance(raw, dict):
                rows.append(raw)
    return rows


def _read_dissent_cards(dissent_dir: Path) -> list[dict[str, Any]]:
    if not dissent_dir.exists():
        return []

    cards: list[dict[str, Any]] = []
    for path in sorted(dissent_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            cards.append(raw)
    return cards


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _derive_version(parent_ids: list[str]) -> str:
    return f"v{len(parent_ids) + 1}"


def run_micro_deliberation(
    *,
    session_dir: str | Path,
    artifact_id: str,
    arena: str,
    proposed_action: str,
    critiques: list[dict[str, Any]],
    panel_state: dict[str, Any],
    accepted_patches: list[dict[str, Any]] | None = None,
    unresolved_dissents: list[dict[str, Any]] | None = None,
    unresolved_dissent_saved: bool | None = None,
) -> dict[str, Any]:
    """Run one structured deliberation round and persist core records.

    This is the MVP micro-round glue for:
    proposal/critique/repair -> governor gate -> commit/snapshot persistence.
    """

    commit_allowed, reason = validate_precommit_action(
        proposed_action,
        critiques,
        panel_state,
        accepted_patches=accepted_patches,
        unresolved_dissents=unresolved_dissents,
        unresolved_dissent_saved=unresolved_dissent_saved,
    )

    action = proposed_action.strip().lower()
    arena_name = parse_enum(arena, DebateArena, "arena").value
    decision = "accept" if commit_allowed else "park"

    root = Path(session_dir)
    root.mkdir(parents=True, exist_ok=True)

    commit_id = f"commit_{uuid4().hex[:10]}"
    event_id = f"event_{uuid4().hex[:10]}"
    now = _now_iso()

    accepted_patches = accepted_patches or []
    unresolved_dissents = unresolved_dissents or []

    latest_commit_ids = [
        str(item.get("commit_id"))
        for item in _read_jsonl(root / "commits.jsonl")
        if isinstance(item, dict) and str(item.get("artifact_id")) == artifact_id and item.get("commit_id")
    ]
    parent_ids = latest_commit_ids[-1:] if latest_commit_ids else []
    open_issues = [
        str(item.get("message", item.get("summary", ""))).strip()
        for item in unresolved_dissents
        if isinstance(item, dict) and str(item.get("status", "")).lower() == "open"
    ]
    open_issues = [issue for issue in open_issues if issue]
    proposed_changes = [
        patch.get("proposed_changes", {})
        for patch in accepted_patches
        if isinstance(patch, dict) and isinstance(patch.get("proposed_changes"), dict)
    ]
    dissent_patch_ids = [
        str(item.get("dissent_id"))
        for item in unresolved_dissents
        if isinstance(item, dict) and item.get("dissent_id")
    ]
    why_not_others = [
        str(item.get("why_not", item.get("counterfactual", ""))).strip()
        for item in unresolved_dissents
        if isinstance(item, dict)
    ]
    why_not_others = [item for item in why_not_others if item] or [
        "no explicit alternatives were recorded in this round"
    ]
    reasons = [str(reason).strip() for reason in [reason] if str(reason).strip()]
    version = _derive_version(parent_ids)

    commit = {
        "commit_id": commit_id,
        "artifact_id": artifact_id,
        "decision": decision,
        "requested_action": action,
        "allowed": commit_allowed,
        "reason": reason,
        "status": "applied" if commit_allowed else "pending",
        "parent_ids": parent_ids,
        "version": version,
        "open_issues": open_issues,
        "proposed_changes": proposed_changes,
        "reasons": reasons,
        "dissent_patch_ids": dissent_patch_ids,
        "why_not_others": why_not_others,
        "timestamp": now,
        "schema_version": 2,
    }

    event = {
        "event_id": event_id,
        "artifact_id": artifact_id,
        "arena": arena_name,
        "type": "micro_deliberation_round",
        "decision": decision,
        "commit_id": commit_id,
        "parent_ids": parent_ids,
        "version": version,
        "open_issues": open_issues,
        "proposed_changes": proposed_changes,
        "reasons": reasons,
        "dissent_patch_ids": dissent_patch_ids,
        "why_not_others": why_not_others,
        "timestamp": now,
        "schema_version": 2,
    }

    snapshot = ensure_current_schema(_read_json(root / "snapshot.json"))
    latest_commits = snapshot.get("latest_commits", [])
    if not isinstance(latest_commits, list):
        latest_commits = []
    latest_commits = [*latest_commits, commit_id]

    snapshot.update(
        {
            "snapshot_id": snapshot.get("snapshot_id", f"snap_{uuid4().hex[:10]}"),
            "latest_commits": latest_commits,
            "next_recommended_arena": arena_name,
            "parent_ids": parent_ids,
            "version": version,
            "open_issues": unresolved_dissents,
            "proposed_changes": accepted_patches,
            "reasons": reasons,
            "dissent_patch_ids": dissent_patch_ids,
            "why_not_others": why_not_others,
            "schema_version": 2,
        }
    )

    _append_jsonl(root / "event_log.jsonl", [event])
    _append_jsonl(root / "commits.jsonl", [commit])
    _write_json(root / "snapshot.json", snapshot)

    if unresolved_dissents and unresolved_dissent_saved:
        dissent_dir = root / "dissent"
        dissent_dir.mkdir(parents=True, exist_ok=True)
        for item in unresolved_dissents:
            if not isinstance(item, dict):
                continue
            dissent_id = str(item.get("dissent_id", "")).strip() or f"dissent_{uuid4().hex[:8]}"
            _write_json(dissent_dir / f"{dissent_id}.json", item)

    return {
        "commit": commit,
        "event": event,
        "snapshot": snapshot,
    }


def build_continuation_pack(
    session_dir: str | Path,
    *,
    goal: str,
    target_artifact_id: str,
    recent_k: int = 20,
    entry_budget: int = 120,
) -> ContinuationPack:
    """Build a continuation pack from persisted session data."""

    root = Path(session_dir)
    snapshot = ensure_current_schema(_read_json(root / "snapshot.json"))
    commits = [ensure_current_schema(entry) for entry in _read_jsonl(root / "commits.jsonl")]
    events = [ensure_current_schema(entry) for entry in _read_jsonl(root / "event_log.jsonl")]
    dissents = [ensure_current_schema(entry) for entry in _read_dissent_cards(root / "dissent")]

    minimal_context, unresolved_conflicts = build_minimal_context(
        snapshot,
        target_artifact_id,
        commits,
        dissents,
        events,
        recent_k=recent_k,
        entry_budget=entry_budget,
    )

    return ContinuationPack(
        goal=goal,
        target_artifact_id=target_artifact_id,
        arena=minimal_context.get("next_recommended_arena"),
        minimal_context=minimal_context,
        unresolved_conflicts=unresolved_conflicts,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.engine",
        description="Build a continuation pack from a persisted session directory.",
    )
    parser.add_argument(
        "--session-dir",
        required=True,
        help="Session directory that may contain snapshot.json, commits.jsonl, event_log.jsonl, dissent/.",
    )
    parser.add_argument("--goal", required=True, help="Continuation goal label.")
    parser.add_argument("--target-artifact-id", required=True, help="Artifact ID to continue from.")
    parser.add_argument("--recent-k", type=int, default=20, help="Keep up to K recent entries per stream.")
    parser.add_argument(
        "--entry-budget",
        type=int,
        default=120,
        help="Total retrieval budget used by continuation trimming strategy.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full continuation pack as JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    pack = build_continuation_pack(
        args.session_dir,
        goal=args.goal,
        target_artifact_id=args.target_artifact_id,
        recent_k=args.recent_k,
        entry_budget=args.entry_budget,
    )

    if args.json:
        payload = {
            "goal": pack.goal,
            "target_artifact_id": pack.target_artifact_id,
            "arena": pack.arena,
            "minimal_context": pack.minimal_context,
            "unresolved_conflicts": pack.unresolved_conflicts,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"goal={pack.goal}")
    print(f"target_artifact_id={pack.target_artifact_id}")
    print(f"arena={pack.arena}")
    print(f"lineage_size={len(pack.minimal_context.get('target_lineage', []))}")
    print(f"commits={len(pack.minimal_context.get('commits', []))}")
    print(f"events={len(pack.minimal_context.get('events', []))}")
    print(f"dissents={len(pack.minimal_context.get('dissents', []))}")
    print(f"unresolved_conflicts={len(pack.unresolved_conflicts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
