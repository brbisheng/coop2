"""Continuation orchestration for session-level retrieval."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .artifacts import ManuscriptCard, normalize_conflict_type
from .governor import validate_precommit_action
from .arenas import load_arenas
from .memory import ContinuationPack, build_minimal_context
from .protocol import (
    DebateArena,
    DebateDecision,
    is_independent_critique,
    parse_enum,
    persona_diversity_score,
)
from .orchestrator import validate_attack_response_alignment, validate_transfer_payload
from .storage import ensure_current_schema


CONTINUE_LIKE_ACTIONS = {"continue", "continue_discussion", "discuss"}
ROUND_STEPS = ("proposal", "critique_a", "critique_b", "transfer", "repair", "decision")

ROUND_EVENT_TYPE = "deliberation.round"
STEP_EVENT_TYPES = {
    "proposal": "deliberation.proposal",
    "critique_a": "deliberation.critique_a",
    "critique_b": "deliberation.critique_b",
    "transfer": "deliberation.transfer",
    "repair": "deliberation.repair",
    "decision": "deliberation.decision",
}


def _build_round_input(
    critiques: list[dict[str, Any]],
    round_input: dict[str, Any] | None,
    accepted_patches: list[dict[str, Any]] | None,
    proposed_action: str,
) -> dict[str, Any]:
    """Normalize legacy callsites into structured round input."""

    normalized = round_input.copy() if isinstance(round_input, dict) else {}
    normalized.setdefault("proposal", {"present": True})
    normalized.setdefault("critique_a", critiques[0] if len(critiques) >= 1 else None)
    normalized.setdefault("critique_b", critiques[1] if len(critiques) >= 2 else None)
    normalized.setdefault(
        "transfer",
        {
            "source_domain_mechanism": "derived from proposal",
            "structural_mapping": "map key constraints/mechanisms to target domain",
            "breakpoints": ["assumption mismatch to be repaired"],
            "new_testable_implications": "predict target-domain signal shifts under mapped constraints",
        },
    )

    default_patch: dict[str, Any] = {}
    for candidate in accepted_patches or []:
        if not isinstance(candidate, dict):
            continue
        proposed = candidate.get("proposed_changes")
        if isinstance(proposed, dict):
            default_patch = proposed
            break

    if len(critiques) >= 2:
        default_addressed = [critiques[0]] if isinstance(critiques[0], dict) else []
        default_not_addressed = [critiques[1]] if isinstance(critiques[1], dict) else []
    elif len(critiques) == 1 and isinstance(critiques[0], dict):
        default_addressed = [critiques[0]]
        default_not_addressed = []
    else:
        default_addressed = []
        default_not_addressed = []

    normalized.setdefault(
        "repair",
        {
            "addressed_attacks": default_addressed,
            "not_addressed_attacks": default_not_addressed,
            "patch": default_patch,
            "new_testable_implication": "derived from accepted patch and critiques",
        },
    )
    normalized.setdefault("decision", {"action": proposed_action})
    return normalized


def _missing_round_steps(round_input: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for step in ROUND_STEPS:
        value = round_input.get(step)
        if value is None:
            missing.append(step)
            continue
        if value in ({}, []):
            missing.append(step)
    return missing


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
        "decision": _present(round_input.get("decision")),
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


def _build_round_quality_metrics(
    *,
    obligation_report: dict[str, Any],
    critiques: list[dict[str, Any]],
    panel_state: dict[str, Any],
    unresolved_dissents: list[dict[str, Any]],
    unresolved_dissent_saved: bool | None,
) -> dict[str, Any]:
    required = obligation_report.get("required", {})
    observed = obligation_report.get("observed", {})

    required_total = sum(int(value) for value in required.values()) if isinstance(required, dict) else 0
    observed_total = 0
    if required_total > 0 and isinstance(required, dict) and isinstance(observed, dict):
        observed_total = sum(min(int(observed.get(key, 0)), int(needed)) for key, needed in required.items())

    obligation_completeness = 1.0 if required_total == 0 else observed_total / required_total

    critique_independence = 0.0
    critique_label = "insufficient_critiques"
    if len(critiques) >= 2:
        critique_independent = is_independent_critique(critiques[0], critiques[1])
        critique_independence = 1.0 if critique_independent else 0.0
        critique_label = "independent" if critique_independent else "overlapping"

    diversity_score = persona_diversity_score(panel_state)
    has_dissent = bool(unresolved_dissents)
    dissent_retained = (not has_dissent) or (unresolved_dissent_saved is True)

    return {
        "obligation_completeness": round(obligation_completeness, 4),
        "obligation_observed": observed_total,
        "obligation_required": required_total,
        "critique_independence": critique_independence,
        "critique_independence_label": critique_label,
        "diversity_score": round(diversity_score, 4),
        "dissent_retained": dissent_retained,
        "dissent_status": "retained" if dissent_retained else "missing",
        "unresolved_dissent_count": len(unresolved_dissents),
    }


def _action_decision(action: str, allowed: bool) -> str:
    if action in {DebateDecision.PARK.value, *CONTINUE_LIKE_ACTIONS}:
        return DebateDecision.PARK.value
    return DebateDecision.ACCEPT.value if allowed else DebateDecision.PARK.value


def allocate_seat(
    *,
    arena: str,
    conflict_type: str,
    agent_module_mix: dict[str, float],
    seat_frequency_history: dict[str, int],
) -> str:
    """Allocate the best seat for an agent using arena/conflict/mix/history signals."""

    score_map = score_seat_candidates(
        arena=arena,
        conflict_type=conflict_type,
        evidence_gaps=[],
        recent_seat_history=[seat for seat, count in seat_frequency_history.items() for _ in range(max(int(count), 0))],
        agent_module_weights=agent_module_mix,
        human_subvalves={},
    )
    if score_map:
        return max(score_map.items(), key=lambda item: item[1])[0]
    return "proposer"


def score_seat_candidates(
    *,
    arena: str,
    conflict_type: str,
    evidence_gaps: list[str],
    recent_seat_history: list[str],
    agent_module_weights: dict[str, float],
    human_subvalves: dict[str, float],
) -> dict[str, float]:
    """Score each seat with conflict/evidence/history/agent-mix signals."""

    arena_specs = load_arenas(Path(__file__).resolve().parents[1] / "config" / "arenas.yaml")
    spec = arena_specs.get(arena)
    seat_cfg = spec.seat_allocation if spec else {}

    base_scores: dict[str, float] = {
        str(seat).strip().lower(): float(score)
        for seat, score in dict(seat_cfg.get("base_scores", {})).items()
        if str(seat).strip()
    }
    if not base_scores:
        base_scores = {"proposer": 1.0, "critic": 1.0, "repairer": 1.0}

    conflict_bias_map = dict(seat_cfg.get("conflict_bias", {}))
    conflict_key = normalize_conflict_type(conflict_type)
    conflict_bias = conflict_bias_map.get(conflict_key, {}) if isinstance(conflict_bias_map, dict) else {}

    module_bias = {
        "economics": {"proposer": 0.25, "critic": 0.15, "repairer": 0.1},
        "psychology": {"critic": 0.30, "proposer": 0.05, "repairer": 0.05},
        "philosophy": {"critic": 0.25, "repairer": 0.15, "proposer": 0.05},
    }
    history_penalty = float(seat_cfg.get("history_penalty", 0.2))

    recent_history = [str(item).strip().lower() for item in recent_seat_history if str(item).strip()]
    seat_frequency_history: dict[str, int] = {}
    for seat in recent_history:
        seat_frequency_history[seat] = seat_frequency_history.get(seat, 0) + 1

    evidence_gap_count = len([gap for gap in evidence_gaps if str(gap).strip()])
    evidence_bias = {
        "proposer": -0.05,
        "critic": 0.08,
        "repairer": 0.18,
    }
    subvalve_bias = {
        "execution_realism": {"repairer": 0.20, "critic": 0.08},
        "bounded_attention": {"critic": 0.15},
        "social_interpretation": {"proposer": 0.10, "critic": 0.06},
        "practical_friction": {"repairer": 0.12, "critic": 0.04},
    }

    scores: dict[str, float] = {}
    for seat, base in base_scores.items():
        score = float(base)
        score += float(conflict_bias.get(seat, 0.0)) if isinstance(conflict_bias, dict) else 0.0

        for module, weight in agent_module_weights.items():
            if not isinstance(weight, (int, float)):
                continue
            score += float(weight) * float(module_bias.get(str(module).strip().lower(), {}).get(seat, 0.0))

        for subvalve, value in human_subvalves.items():
            if not isinstance(value, (int, float)):
                continue
            score += float(value) * float(subvalve_bias.get(str(subvalve).strip().lower(), {}).get(seat, 0.0))

        score += evidence_gap_count * evidence_bias.get(seat, 0.0)

        score -= history_penalty * float(seat_frequency_history.get(seat, 0))
        scores[seat] = round(score, 6)

    return scores


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


def _write_ledger_record(root: Path, *, ledger_name: str, record_id: str, payload: dict[str, Any]) -> str:
    """Persist one ledger record and return a stable reference path."""

    rel_path = Path("ledgers") / ledger_name / f"{record_id}.json"
    _write_json(root / rel_path, payload)
    return rel_path.as_posix()


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
    evidence_gaps: list[str] = []
    evidence_refs_by_module: dict[str, list[str]] = {}
    discipline_payload_by_module: dict[str, dict[str, Any]] = {}

    for item in audit_results:
        if not isinstance(item, dict):
            continue
        module_name = str(item.get("module", "")).strip() or "unknown"
        audit = item.get("audit", {})
        if not isinstance(audit, dict):
            continue
        observations.extend(str(x) for x in audit.get("observations", []))
        criticisms.extend(str(x) for x in audit.get("criticisms", []))
        revisions.extend(str(x) for x in audit.get("revisions", []))
        risks.extend(str(x) for x in audit.get("risks", []))
        questions.extend(str(x) for x in audit.get("questions", []))
        evidence_needs.extend(str(x) for x in audit.get("evidence_needs", []))
        evidence_refs_by_module[module_name] = [
            str(ref).strip() for ref in audit.get("evidence_refs", []) if str(ref).strip()
        ]
        evidence_gap = str(audit.get("evidence_gap", "")).strip()
        if evidence_gap:
            evidence_gaps.append(evidence_gap)

        module_discipline_payload = audit.get("discipline_payload")
        if isinstance(module_discipline_payload, dict):
            module_entry = module_discipline_payload.get(module_name)
            if isinstance(module_entry, dict):
                discipline_payload_by_module[module_name] = module_entry
            else:
                discipline_payload_by_module[module_name] = module_discipline_payload

    unique_claims = sorted(set(revisions + risks + questions))
    covered_claims = set(revisions)
    covered_claims.update(risk for risk in risks if "missing" not in risk.lower())
    uncovered_key_claims = [claim for claim in unique_claims if claim not in covered_claims]

    modules_with_refs = sum(1 for refs in evidence_refs_by_module.values() if refs)
    evidence_coverage_rate = (modules_with_refs / len(modules)) if modules else 1.0

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
        "evidence_gaps": evidence_gaps,
        "evidence_refs_by_module": evidence_refs_by_module,
        "discipline_payload_by_module": discipline_payload_by_module,
        "evidence_coverage_rate": round(evidence_coverage_rate, 4),
        "uncovered_key_claims": uncovered_key_claims,
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
    soul_profile: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run one structured deliberation round and persist core records.

    This is the MVP micro-round glue for:
    proposal/critique/repair -> governor gate -> commit/snapshot persistence.
    """

    action = proposed_action.strip().lower()
    arena_name = parse_enum(arena, DebateArena, "arena").value
    round_input_data = _build_round_input(critiques, round_input, accepted_patches, proposed_action=action)

    repair_output = round_input_data.get("repair") if isinstance(round_input_data.get("repair"), dict) else {}
    transfer_output_text = json.dumps(round_input_data.get("transfer", {}), ensure_ascii=False)
    transfer_valid, transfer_reasons, transfer_payload = validate_transfer_payload(transfer_output_text)
    if not transfer_valid:
        round_input_data["transfer"] = None

    transfer_breakpoints = []
    if isinstance(transfer_payload, dict):
        raw_breakpoints = transfer_payload.get("breakpoints")
        if isinstance(raw_breakpoints, list):
            transfer_breakpoints = [str(item).strip() for item in raw_breakpoints if str(item).strip()]

    if transfer_breakpoints and isinstance(repair_output, dict):
        repair_output.setdefault("responded_breakpoints", transfer_breakpoints)

    alignment = validate_attack_response_alignment(critiques=critiques, repair_output=repair_output)
    if alignment["unresolved_dissents"]:
        unresolved_dissents = [*(unresolved_dissents or []), *alignment["unresolved_dissents"]]

    missing_steps = _missing_round_steps(round_input_data)
    missing_obligations, obligation_report = _required_obligation_report(arena_name, round_input_data)

    if missing_steps:
        commit_allowed = action in {DebateDecision.PARK.value, *CONTINUE_LIKE_ACTIONS}
        reason = (
            "structured round input incomplete: "
            + ", ".join(missing_steps)
            + "; only park/continue allowed"
        )
    elif missing_obligations:
        commit_allowed = action in {DebateDecision.PARK.value, *CONTINUE_LIKE_ACTIONS}
        reason = (
            "required obligations not satisfied: "
            + ", ".join(missing_obligations)
            + "; only park/continue allowed"
        )
    elif not alignment["is_aligned"]:
        action = "continue_discussion"
        commit_allowed = True
        reason = "attack-response alignment failed; downgrade action to continue_discussion"
    else:
        commit_allowed, reason = validate_precommit_action(
            proposed_action,
            critiques,
            panel_state,
            accepted_patches=accepted_patches,
            unresolved_dissents=unresolved_dissents,
            unresolved_dissent_saved=unresolved_dissent_saved,
        )

    quality_metrics = _build_round_quality_metrics(
        obligation_report=obligation_report,
        critiques=critiques,
        panel_state=panel_state,
        unresolved_dissents=unresolved_dissents or [],
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
    normalized_unresolved_dissents: list[dict[str, Any]] = []
    for item in unresolved_dissents:
        if not isinstance(item, dict):
            continue
        normalized_item = dict(item)
        normalized_item["conflict_type"] = normalize_conflict_type(
            normalized_item.get("conflict_type", "execution")
        )
        normalized_unresolved_dissents.append(normalized_item)
    unresolved_dissents = normalized_unresolved_dissents
    perspective_audits = perspective_audits or []
    audit_summary = summarize_audit_batch(perspective_audits)
    quality_metrics["evidence_coverage_rate"] = audit_summary.get("evidence_coverage_rate", 0.0)
    quality_metrics["uncovered_key_claims"] = audit_summary.get("uncovered_key_claims", [])

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
    evidence_gap_issues = [f"evidence_gap: {gap}" for gap in audit_summary.get("evidence_gaps", []) if str(gap).strip()]
    open_issues.extend(evidence_gap_issues)
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
    conflict_types = [
        str(item.get("conflict_type"))
        for item in unresolved_dissents
        if isinstance(item, dict) and item.get("conflict_type")
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
    if evidence_gap_issues:
        reasons.append("evidence gaps remain unresolved")
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
        "conflict_types": conflict_types,
        "why_not_others": why_not_others,
        "timestamp": now,
        "schema_version": 3,
        "perspective_audits": perspective_audits,
        "patch_rationale": audit_summary["rationale"],
        "quality_metrics": quality_metrics,
        "attack_response_alignment": alignment,
    }

    event = {
        "event_id": event_id,
        "artifact_id": artifact_id,
        "arena": arena_name,
        "type": ROUND_EVENT_TYPE,
        "decision": decision,
        "commit_id": commit_id,
        "parent_ids": parent_ids,
        "version": version,
        "open_issues": open_issues,
        "proposed_changes": proposed_changes,
        "reasons": reasons,
        "dissent_patch_ids": dissent_patch_ids,
        "conflict_types": conflict_types,
        "why_not_others": why_not_others,
        "timestamp": now,
        "schema_version": 3,
        "perspective_audits": perspective_audits,
        "patch_rationale": audit_summary["rationale"],
        "audit_summary": audit_summary,
        "quality_metrics": quality_metrics,
        "attack_response_alignment": alignment,
    }

    cognitive_output = {
        "cognitive_output_id": f"cog_{event_id}",
        "event_id": event_id,
        "commit_id": commit_id,
        "artifact_id": artifact_id,
        "arena": arena_name,
        "decision": decision,
        "quality_metrics": quality_metrics,
        "audit_summary": audit_summary,
        "timestamp": now,
        "schema_version": 1,
    }
    if dry_run:
        cognitive_output_ref = f"dry_run/ledgers/cognitive/{cognitive_output['cognitive_output_id']}.json"
    else:
        cognitive_output_ref = _write_ledger_record(
            root,
            ledger_name="cognitive",
            record_id=cognitive_output["cognitive_output_id"],
            payload=cognitive_output,
        )

    normalized_soul_profile = dict(soul_profile) if isinstance(soul_profile, dict) else {}
    soul_trace = {
        "soul_trace_id": f"soul_{event_id}",
        "event_id": event_id,
        "artifact_id": artifact_id,
        "cognitive_output_ref": cognitive_output_ref,
        "soul_profile": normalized_soul_profile,
        "timestamp": now,
        "schema_version": 1,
    }
    if dry_run:
        soul_trace_ref = f"dry_run/ledgers/soul/{soul_trace['soul_trace_id']}.json"
    else:
        soul_trace_ref = _write_ledger_record(
            root,
            ledger_name="soul",
            record_id=soul_trace["soul_trace_id"],
            payload=soul_trace,
        )
    event["cognitive_output_ref"] = cognitive_output_ref
    event["soul_trace_ref"] = soul_trace_ref

    step_events = [
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": STEP_EVENT_TYPES["proposal"],
            "round_event_id": event_id,
            "step": "proposal",
            "payload": round_input_data.get("proposal"),
            "timestamp": now,
        },
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": STEP_EVENT_TYPES["critique_a"],
            "round_event_id": event_id,
            "step": "critique_a",
            "payload": round_input_data.get("critique_a"),
            "timestamp": now,
        },
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": STEP_EVENT_TYPES["critique_b"],
            "round_event_id": event_id,
            "step": "critique_b",
            "payload": round_input_data.get("critique_b"),
            "timestamp": now,
        },
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": STEP_EVENT_TYPES["transfer"],
            "round_event_id": event_id,
            "step": "transfer",
            "payload": round_input_data.get("transfer"),
            "timestamp": now,
        },
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": STEP_EVENT_TYPES["repair"],
            "round_event_id": event_id,
            "step": "repair",
            "payload": round_input_data.get("repair"),
            "timestamp": now,
        },
        {
            "event_id": f"event_{uuid4().hex[:10]}",
            "artifact_id": artifact_id,
            "arena": arena_name,
            "type": STEP_EVENT_TYPES["decision"],
            "round_event_id": event_id,
            "step": "decision",
            "payload": {
                "decision": decision,
                "allowed": commit_allowed,
                "reason": reason,
                "missing_steps": missing_steps,
                "missing_obligations": missing_obligations,
                "obligation_report": obligation_report,
                "quality_metrics": quality_metrics,
                "attack_response_alignment": alignment,
                "transfer_validation": {
                    "is_valid": transfer_valid,
                    "reasons": transfer_reasons,
                },
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

    if dry_run:
        artifact_ref = f"dry_run/artifacts/{artifact_id}/{version}.json"
    else:
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

    if not dry_run:
        _append_jsonl(root / "event_log.jsonl", [*step_events, event])
        _append_jsonl(root / "commits.jsonl", [commit])
        _write_json(root / "snapshot.json", snapshot)

    if (not dry_run) and unresolved_dissents and unresolved_dissent_saved:
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
        "dry_run": dry_run,
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




def build_manuscript_draft_cards_from_records(
    *,
    snapshot: dict[str, Any],
    commits: list[dict[str, Any]],
    dissents: list[dict[str, Any]],
    artifact_id: str | None = None,
) -> list[ManuscriptCard]:
    """Build manuscript draft cards from snapshot/commit/dissent records."""

    snapshot_id = str(snapshot.get("snapshot_id", "")).strip() or None
    latest_commit_ids = snapshot.get("latest_commits", [])
    latest_commit_id = None
    if isinstance(latest_commit_ids, list) and latest_commit_ids:
        latest_commit_id = str(latest_commit_ids[-1]).strip() or None

    target_commits = [item for item in commits if isinstance(item, dict)]
    if artifact_id:
        target_commits = [
            item for item in target_commits if str(item.get("artifact_id", "")).strip() == artifact_id
        ]

    if not target_commits:
        return []

    open_dissents = [
        item
        for item in dissents
        if isinstance(item, dict) and str(item.get("status", "open")).strip().lower() == "open"
    ]

    cards: list[ManuscriptCard] = []
    for index, commit in enumerate(target_commits, start=1):
        commit_id = str(commit.get("commit_id", "")).strip()
        commit_artifact_id = str(commit.get("artifact_id", artifact_id or "artifact_main")).strip()
        open_issues = commit.get("open_issues", [])
        commit_conflicts = [item for item in open_issues if isinstance(item, str) and item.strip()]
        dissent_conflicts = [
            str(item.get("summary", item.get("message", ""))).strip()
            for item in open_dissents
            if str(item.get("artifact_id", commit_artifact_id)).strip() == commit_artifact_id
        ]
        pending_conflicts = [item for item in [*commit_conflicts, *dissent_conflicts] if item]

        evidence_refs = [f"commit:{commit_id}"] if commit_id else []
        evidence_refs.extend(
            f"dissent:{str(item.get('dissent_id')).strip()}"
            for item in open_dissents
            if str(item.get("artifact_id", commit_artifact_id)).strip() == commit_artifact_id
            and str(item.get("dissent_id", "")).strip()
        )

        alternatives = [
            item
            for item in commit.get("why_not_others", [])
            if isinstance(item, str) and item.strip()
        ]

        source_commit_id = commit_id or latest_commit_id
        card = ManuscriptCard(
            manuscript_id=f"ms_{commit_artifact_id}_{index}",
            artifact_id=commit_artifact_id,
            chapter_slot=f"chapter_{index}",
            evidence_refs=evidence_refs,
            pending_conflicts=pending_conflicts,
            alternative_explanations=alternatives,
            source_snapshot_id=snapshot_id,
            source_commit_id=source_commit_id,
        )
        cards.append(card)

    return cards


def export_manuscript_skeleton(
    session_dir: str | Path,
    *,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    """Export manuscript writing skeleton from persisted records."""

    root = Path(session_dir)
    snapshot = ensure_current_schema(_read_json(root / "snapshot.json"))
    commits = [ensure_current_schema(entry) for entry in _read_jsonl(root / "commits.jsonl")]
    dissents = [ensure_current_schema(entry) for entry in _read_dissent_cards(root / "dissent")]

    cards = build_manuscript_draft_cards_from_records(
        snapshot=snapshot,
        commits=commits,
        dissents=dissents,
        artifact_id=artifact_id,
    )

    return {
        "snapshot_id": snapshot.get("snapshot_id"),
        "artifact_id": artifact_id,
        "manuscript_cards": [card.to_dict() for card in cards],
    }

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
