"""Continuation orchestration for session-level retrieval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .memory import ContinuationPack, build_minimal_context


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
    snapshot = _read_json(root / "snapshot.json")
    commits = _read_jsonl(root / "commits.jsonl")
    events = _read_jsonl(root / "event_log.jsonl")
    dissents = _read_dissent_cards(root / "dissent")

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
