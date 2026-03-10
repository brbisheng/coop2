"""Continuation orchestration for session-level retrieval."""

from __future__ import annotations

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
