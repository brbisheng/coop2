"""Continuation orchestration for session-level retrieval."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .governor import validate_precommit_action
from .arenas import load_arenas
from .memory import ContinuationPack, build_minimal_context
from .protocol import DebateArena, DebateDecision, parse_enum
from .storage import ensure_current_schema


CONTINUE_LIKE_ACTIONS = {"continue", "continue_discussion", "discuss"}


def _build_round_input(
    critiques: list[dict[str, Any]],
    round_input: dict[str, Any] | None,
    accepted_patches: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Normalize legacy callsites into structured round input."""

    normalized = round_input.copy() if isinstance(round_input, dict) else {}
    normalized.setdefault("proposal", {"present": True})
    normalized.setdefault("critique_a", critiques[0] if len(critiques) >= 1 else None)
    normalized.setdefault("critique_b", critiques[1] if len(critiques) >= 2 else None)
    normalized.setdefault("repair", {"present": bool(accepted_patches)})
    normalized.setdefault("governor_decision", None)
    return normalized


def _required_obligation_report(arena_name: str, round_input: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """Validate required obligations in arena config and return missing items."""

    arena_specs = load_arenas(Path(__file__).resolve().parents[1] / "config" / "arenas.yaml")
    spec = arena_specs.get(arena_name)
    required = spec.required_obligations if spec else {}

    def _present(value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, dict) and "present" in value:
            return int(bool(value.get("present")))
        return int(bool(value))

    critiques_present = _present(round_input.get("critique_a")) + _present(round_input.get("critique_b"))
    observed = {
        "propose": _present(round_input.get("proposal")),
        "independent_critiques": critiques_present,
        "repair_or_merge": _present(round_input.get("repair")),
        "governor_decision": _present(round_input.get("governor_decision")),
    }

    missing: list[str] = []
    for obligation, needed in required.items():
        count = int(needed)
        current = int(observed.get(obligation, 0))
        if current < count:
            missing.append(f"{obligation} ({current}/{count})")

    report = {
        "arena": arena_name,
        "required": required,
        "observed": observed,
        "missing": missing,
    }
    return missing, report


def _action_decision(action: str, allowed: bool) -> str:
    if action in {DebateDecision.PARK.value, *CONTINUE_LIKE_ACTIONS}:
        return DebateDecision.PARK.value
    return DebateDecision.ACCEPT.value if allowed else DebateDecision.PARK.value


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


def _persist_artifact_version(
    root: Path,
    *,
    artifact_id: str,
    version: str,
    commit: dict[str, Any],
    event: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    artifact_rel_path = Path("artifacts") / artifact_id / f"{version}.json"
    artifact_payload = {
        "artifact_id": artifact_id,
        "parent_ids": commit.get("parent_ids", []),
        "version": version,
        "open_issues": commit.get("open_issues", []),
        "proposed_changes": commit.get("proposed_changes", []),
        "why_not_others": commit.get("why_not_others", []),
        "dissent_patch_ids": commit.get("dissent_patch_ids", []),
        "commit_id": commit.get("commit_id"),
        "event_id": event.get("event_id"),
        "decision": commit.get("decision"),
        "status": commit.get("status"),
        "timestamp": commit.get("timestamp"),
        "schema_version": 3,
    }
    _write_json(root / artifact_rel_path, artifact_payload)
    return artifact_rel_path.as_posix(), artifact_payload


def load_artifact_version(
    session_dir: str | Path,
    *,
    artifact_id: str,
    version: str | None = None,
) -> dict[str, Any]:
    """Load one artifact version from artifacts/ layout.

    When version is omitted, the snapshot artifact head pointer is used.
    """

    root = Path(session_dir)
    snapshot = ensure_current_schema(_read_json(root / "snapshot.json"))

    if version is None:
        heads = snapshot.get("artifact_heads", {})
        head = heads.get(artifact_id) if isinstance(heads, dict) else None
        if isinstance(head, dict):
            version = str(head.get("version", "")).strip() or None

    if version is None:
        raise ValueError(f"No artifact head pointer found for {artifact_id}")

    payload = _read_json(root / "artifacts" / artifact_id / f"{version}.json")
    if not payload:
        raise FileNotFoundError(f"Artifact version not found: {artifact_id}@{version}")
    return ensure_current_schema(payload)




def run_perspective_audit_batch(
    *,
    modules: list[Any],
    artifact: dict[str, Any],
    local_context: dict[str, Any],
    unresolved_conflicts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run all perspective modules and return validated structured outputs."""

    from .perspectives import validate_perspective_output

    results: list[dict[str, Any]] = []
    for module in modules:
        module_name = str(getattr(module, "name", module.__class__.__name__)).strip().lower()
        payload = module.audit(artifact, local_context, unresolved_conflicts)
        validate_perspective_output(payload)
        results.append(
            {
                "module": module_name,
                "module_version": str(getattr(module, "version", "unknown")),
                "audit": payload,
            }
        )
    return results


def summarize_audit_batch(audit_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate module outputs for event payloads and patch rationale generation."""

    modules = [str(item.get("module", "")).strip() for item in audit_results if isinstance(item, dict)]
    confidence_values = [
        float(item.get("audit", {}).get("confidence"))
        for item in audit_results
        if isinstance(item, dict)
    ]
    avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0

    observations: list[str] = []
    criticisms: list[str] = []
    revisions: list[str] = []
    risks: list[str] = []
    questions: list[str] = []
    evidence_needs: list[str] = []

    for item in audit_results:
        if not isinstance(item, dict):
            continue
        audit = item.get("audit", {})
        if not isinstance(audit, dict):
            continue
        observations.extend(str(x) for x in audit.get("observations", []))
        criticisms.extend(str(x) for x in audit.get("criticisms", []))
        revisions.extend(str(x) for x in audit.get("revisions", []))
        risks.extend(str(x) for x in audit.get("risks", []))
        questions.extend(str(x) for x in audit.get("questions", []))
        evidence_needs.extend(str(x) for x in audit.get("evidence_needs", []))

    rationale = (
        f"modules={','.join(modules) or 'none'}; avg_confidence={avg_confidence:.2f}; "
        f"revisions={len(revisions)}; risks={len(risks)}"
    )

    return {
        "modules": modules,
        "module_count": len(modules),
        "avg_confidence": avg_confidence,
        "observations": observations,
        "criticisms": criticisms,
        "revisions": revisions,
        "risks": risks,
        "questions": questions,
        "evidence_needs": evidence_needs,
        "rationale": rationale,
    }

def run_micro_deliberation(
    *,
    session_dir: str | Path,
    artifact_id: str,
    arena: str,
    proposed_action: str,
    critiques: list[dict[str, Any]],
    round_input: dict[str, Any] | None = None,
    panel_state: dict[str, Any],
    accepted_patches: list[dict[str, Any]] | None = None,
    unresolved_dissents: list[dict[str, Any]] | None = None,
    unresolved_dissent_saved: bool | None = None,
    perspective_audits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one structured deliberation round and persist core records.

    This is the MVP micro-round glue for:
    proposal/critique/repair -> governor gate -> commit/snapshot persistence.
    """

    action = proposed_action.strip().lower()
    arena_name = parse_enum(arena, DebateArena, "arena").value
    round_input_data = _build_round_input(critiques, round_input, accepted_patches)
    missing_obligations, obligation_report = _required_obligation_report(arena_name, round_input_data)

    if missing_obligations:
        commit_allowed = action in {DebateDecision.PARK.value, *CONTINUE_LIKE_ACTIONS}
        reason = (
            "required obligations not satisfied: "
            + ", ".join(missing_obligations)
            + "; only park/continue allowed"
        )
    else:
        commit_allowed, reason = validate_precommit_action(
            proposed_action,
            critiques,
            panel_state,
            accepted_patches=accepted_patches,
            unresolved_dissents=unresolved_dissents,
            unresolved_dissent_saved=unresolved_dissent_saved,
        )
    decision = _action_decision(action, commit_allowed)

    root = Path(session_dir)
    root.mkdir(parents=True, exist_ok=True)

    commit_id = f"commit_{uuid4().hex[:10]}"
    event_id = f"event_{uuid4().hex[:10]}"
    now = _now_iso()

    accepted_patches = accepted_patches or []
    unresolved_dissents = unresolved_dissents or []
    perspective_audits = perspective_audits or []
    audit_summary = summarize_audit_batch(perspective_audits)

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
        "schema_version": 3,
        "perspective_audits": perspective_audits,
        "patch_rationale": audit_summary["rationale"],
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
        "schema_version": 3,
        "perspective_audits": perspective_audits,
        "patch_rationale": audit_summary["rationale"],
        "audit_summary": audit_summary,
    }

    step_events = [
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": "micro_deliberation_step",
            "round_event_id": event_id,
            "step": "proposal",
            "payload": round_input_data.get("proposal"),
            "timestamp": now,
        },
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": "micro_deliberation_step",
            "round_event_id": event_id,
            "step": "critique_a",
            "payload": round_input_data.get("critique_a"),
            "timestamp": now,
        },
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": "micro_deliberation_step",
            "round_event_id": event_id,
            "step": "critique_b",
            "payload": round_input_data.get("critique_b"),
            "timestamp": now,
        },
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": "micro_deliberation_step",
            "round_event_id": event_id,
            "step": "repair",
            "payload": round_input_data.get("repair"),
            "timestamp": now,
        },
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": "micro_deliberation_step",
            "round_event_id": event_id,
            "step": "governor_decision",
            "payload": {
                "decision": decision,
                "allowed": commit_allowed,
                "reason": reason,
                "missing_obligations": missing_obligations,
                "obligation_report": obligation_report,
            },
            "timestamp": now,
        },
    ]
    step_events = [item for item in step_events if item.get("payload") not in (None, {}, [])]
    event["round_input"] = round_input_data
    event["obligation_report"] = obligation_report

    snapshot = ensure_current_schema(_read_json(root / "snapshot.json"))
    latest_commits = snapshot.get("latest_commits", [])
    if not isinstance(latest_commits, list):
        latest_commits = []
    latest_commits = [*latest_commits, commit_id]

    artifact_ref, _artifact_payload = _persist_artifact_version(
        root,
        artifact_id=artifact_id,
        version=version,
        commit=commit,
        event=event,
    )

    artifact_heads = snapshot.get("artifact_heads", {})
    if not isinstance(artifact_heads, dict):
        artifact_heads = {}
    artifact_heads[artifact_id] = {
        "artifact_id": artifact_id,
        "version": version,
        "path": artifact_ref,
        "commit_id": commit_id,
    }

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
            "schema_version": 3,
            "artifact_heads": artifact_heads,
            "perspective_audits": perspective_audits,
            "patch_rationale": audit_summary["rationale"],
            "audit_summary": audit_summary,
        }
    )

    commit["artifact_ref"] = artifact_ref
    event["artifact_ref"] = artifact_ref

    commit = ensure_current_schema(commit)
    event = ensure_current_schema(event)
    snapshot = ensure_current_schema(snapshot)

    _append_jsonl(root / "event_log.jsonl", [*step_events, event])
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
    resolved_target_artifact_id = target_artifact_id
    heads = snapshot.get("artifact_heads", {})
    if isinstance(heads, dict) and target_artifact_id in heads:
        head = heads.get(target_artifact_id)
        if isinstance(head, dict):
            resolved_target_artifact_id = str(head.get("artifact_id", target_artifact_id))
    commits = [ensure_current_schema(entry) for entry in _read_jsonl(root / "commits.jsonl")]
    events = [ensure_current_schema(entry) for entry in _read_jsonl(root / "event_log.jsonl")]
    dissents = [ensure_current_schema(entry) for entry in _read_dissent_cards(root / "dissent")]

    minimal_context, unresolved_conflicts = build_minimal_context(
        snapshot,
        resolved_target_artifact_id,
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
