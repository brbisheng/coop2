"""Service-layer API facade with strict JSON contracts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from .engine import (
    _build_round_input,
    build_continuation_pack,
    export_manuscript_skeleton,
    load_artifact_version,
    run_micro_deliberation,
)
from .memory import ContinuationPack
from .protocol import DebateArena, ModelValidationError, parse_enum
from .orchestrator import build_seat_context
from .soul import SoulValidationError, strip_soul_fields_for_governance, validate_soul_profile


class ServiceApiValidationError(ValueError):
    """Raised when a service API payload fails boundary validation."""



def _require_mapping(payload: dict[str, Any] | None, *, endpoint: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ServiceApiValidationError(f"{endpoint} request must be a JSON object")
    return payload


def _missing_required(payload: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    return [field for field in required if field not in payload]



@dataclass(slots=True)
class RoundRunRequest:
    """Internal request model for round execution."""

    session_dir: str
    artifact_id: str
    arena: str
    proposed_action: str
    critiques: list[dict[str, Any]]
    panel_state: dict[str, Any]
    round_input: dict[str, Any] | None
    accepted_patches: list[dict[str, Any]]
    unresolved_dissents: list[dict[str, Any]]
    unresolved_dissent_saved: bool
    perspective_audits: list[dict[str, Any]]
    soul_profile: dict[str, Any]
    seat_contexts: dict[str, dict[str, Any]]
    dry_run: bool

    @classmethod
    def from_api_json(cls, payload: dict[str, Any] | None) -> "RoundRunRequest":
        raw = _require_mapping(payload, endpoint="run_round")
        required = (
            "session_dir",
            "artifact_id",
            "arena",
            "proposed_action",
            "critiques",
            "panel_state",
        )
        missing = _missing_required(raw, required)
        if missing:
            raise ServiceApiValidationError(f"run_round missing required fields: {missing}")

        try:
            arena = parse_enum(raw.get("arena", ""), DebateArena, "arena").value
        except ModelValidationError as exc:
            raise ServiceApiValidationError(str(exc)) from exc

        try:
            soul_profile = validate_soul_profile(raw.get("soul_profile")).to_dict()
        except SoulValidationError as exc:
            raise ServiceApiValidationError(str(exc)) from exc

        critiques = raw.get("critiques")
        if not isinstance(critiques, list):
            raise ServiceApiValidationError("run_round.critiques must be a list")

        panel_state = raw.get("panel_state")
        if not isinstance(panel_state, dict):
            raise ServiceApiValidationError("run_round.panel_state must be an object")
        panel_state = strip_soul_fields_for_governance(panel_state)

        round_input = raw.get("round_input")
        if round_input is not None and not isinstance(round_input, dict):
            raise ServiceApiValidationError("run_round.round_input must be an object when provided")

        accepted_patches = raw.get("accepted_patches", [])
        unresolved_dissents = raw.get("unresolved_dissents", [])
        perspective_audits = raw.get("perspective_audits", [])

        for field_name, value in (
            ("accepted_patches", accepted_patches),
            ("unresolved_dissents", unresolved_dissents),
            ("perspective_audits", perspective_audits),
        ):
            if not isinstance(value, list):
                raise ServiceApiValidationError(f"run_round.{field_name} must be a list")

        seat_contexts_raw = raw.get("seat_contexts", {})
        if not isinstance(seat_contexts_raw, dict):
            raise ServiceApiValidationError("run_round.seat_contexts must be an object when provided")

        return cls(
            session_dir=str(raw["session_dir"]),
            artifact_id=str(raw["artifact_id"]),
            arena=arena,
            proposed_action=str(raw["proposed_action"]),
            critiques=[item for item in critiques if isinstance(item, dict)],
            panel_state=panel_state,
            round_input=round_input,
            accepted_patches=[item for item in accepted_patches if isinstance(item, dict)],
            unresolved_dissents=[item for item in unresolved_dissents if isinstance(item, dict)],
            unresolved_dissent_saved=bool(raw.get("unresolved_dissent_saved", False)),
            perspective_audits=[item for item in perspective_audits if isinstance(item, dict)],
            soul_profile=soul_profile,
            seat_contexts={
                str(seat).strip().lower(): dict(ctx)
                for seat, ctx in seat_contexts_raw.items()
                if str(seat).strip() and isinstance(ctx, dict)
            },
            dry_run=bool(raw.get("dry_run", False)),
        )


@dataclass(slots=True)
class ContinuationPackRequest:
    session_dir: str
    goal: str
    target_artifact_id: str
    recent_k: int
    entry_budget: int

    @classmethod
    def from_api_json(cls, payload: dict[str, Any] | None) -> "ContinuationPackRequest":
        raw = _require_mapping(payload, endpoint="build_continuation_pack")
        required = ("session_dir", "goal", "target_artifact_id")
        missing = _missing_required(raw, required)
        if missing:
            raise ServiceApiValidationError(f"build_continuation_pack missing required fields: {missing}")

        return cls(
            session_dir=str(raw["session_dir"]),
            goal=str(raw["goal"]),
            target_artifact_id=str(raw["target_artifact_id"]),
            recent_k=int(raw.get("recent_k", 20)),
            entry_budget=int(raw.get("entry_budget", 120)),
        )


@dataclass(slots=True)
class ArtifactReadRequest:
    session_dir: str
    artifact_id: str
    version: str | None

    @classmethod
    def from_api_json(cls, payload: dict[str, Any] | None) -> "ArtifactReadRequest":
        raw = _require_mapping(payload, endpoint="read_artifact")
        required = ("session_dir", "artifact_id")
        missing = _missing_required(raw, required)
        if missing:
            raise ServiceApiValidationError(f"read_artifact missing required fields: {missing}")

        version = raw.get("version")
        return cls(
            session_dir=str(raw["session_dir"]),
            artifact_id=str(raw["artifact_id"]),
            version=str(version) if version is not None else None,
        )




@dataclass(slots=True)
class ManuscriptExportRequest:
    session_dir: str
    artifact_id: str | None

    @classmethod
    def from_api_json(cls, payload: dict[str, Any] | None) -> "ManuscriptExportRequest":
        raw = _require_mapping(payload, endpoint="export_manuscript")
        if "session_dir" not in raw:
            raise ServiceApiValidationError("export_manuscript missing required fields: ['session_dir']")
        artifact_id = raw.get("artifact_id")
        return cls(
            session_dir=str(raw["session_dir"]),
            artifact_id=str(artifact_id) if artifact_id is not None else None,
        )

@dataclass(slots=True)
class ContinuationPackResponse:
    goal: str
    target_artifact_id: str
    arena: str | None
    minimal_context: dict[str, Any]
    unresolved_conflicts: list[dict[str, Any]]

    @classmethod
    def from_internal(cls, pack: ContinuationPack) -> "ContinuationPackResponse":
        return cls(
            goal=pack.goal,
            target_artifact_id=pack.target_artifact_id,
            arena=pack.arena,
            minimal_context=pack.minimal_context,
            unresolved_conflicts=pack.unresolved_conflicts,
        )

    def to_api_json(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "target_artifact_id": self.target_artifact_id,
            "arena": self.arena,
            "minimal_context": self.minimal_context,
            "unresolved_conflicts": self.unresolved_conflicts,
        }


def _append_round_audit_trace(
    *,
    session_dir: str,
    artifact_id: str,
    round_input: dict[str, Any],
    seat_contexts: dict[str, dict[str, Any]],
) -> None:
    trace_dir = Path(session_dir) / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / "run_round_audit_trace.jsonl"

    seat_context_summary = {
        seat: sorted(context.keys())
        for seat, context in seat_contexts.items()
        if isinstance(context, dict)
    }

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifact_id": artifact_id,
        "round_input": round_input,
        "seat_context_summary": seat_context_summary,
    }
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _next_trace_round_index(trace_dir: Path) -> int:
    pattern = re.compile(r"^round_(\d{4})_seat_proposer_utterance_chain\.json$")
    indices: list[int] = []
    for path in trace_dir.glob("round_*_seat_*_utterance_chain.json"):
        matched = pattern.match(path.name)
        if matched:
            indices.append(int(matched.group(1)))
    return (max(indices) + 1) if indices else 1


def _write_seat_chain_traces(
    *,
    session_dir: str,
    round_index: int,
    round_input: dict[str, Any],
    seat_contexts: dict[str, dict[str, Any]],
) -> None:
    trace_dir = Path(session_dir) / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    seat_to_round_key = {
        "proposer": "proposal",
        "critic_a": "critique_a",
        "critic_b": "critique_b",
        "transfer_seat": "transfer",
        "repairer": "repair",
        "decision": "decision",
    }
    now = datetime.now(timezone.utc).isoformat()
    for seat, round_key in seat_to_round_key.items():
        output_payload = round_input.get(round_key)
        trace_payload = {
            "timestamp": now,
            "round_index": round_index,
            "seat": seat,
            "input_context": seat_contexts.get(seat, {}),
            "output": output_payload,
        }
        trace_path = trace_dir / f"round_{round_index:04d}_seat_{seat}_utterance_chain.json"
        trace_path.write_text(json.dumps(trace_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_round_report(
    *,
    session_dir: str,
    round_index: int,
    seat_contexts: dict[str, dict[str, Any]],
    final_round_input: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    trace_dir = Path(session_dir) / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    event_payload = result.get("event", {}) if isinstance(result.get("event"), dict) else {}
    commit_payload = result.get("commit", {}) if isinstance(result.get("commit"), dict) else {}
    alignment = event_payload.get("attack_response_alignment", {}) if isinstance(event_payload.get("attack_response_alignment"), dict) else {}
    transfer_payload = final_round_input.get("transfer") if isinstance(final_round_input.get("transfer"), dict) else {}

    seat_sampling_params = {
        seat: (ctx.get("sampling") if isinstance(ctx.get("sampling"), dict) else {})
        for seat, ctx in seat_contexts.items()
        if isinstance(ctx, dict)
    }
    context_summary = {
        seat: sorted(ctx.keys())
        for seat, ctx in seat_contexts.items()
        if isinstance(ctx, dict)
    }
    attack_points = []
    for key in ("critique_a", "critique_b"):
        critique = final_round_input.get(key)
        if isinstance(critique, dict):
            labels = critique.get("attack_labels", [])
            if isinstance(labels, list):
                attack_points.extend(str(item) for item in labels if str(item).strip())

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "round_index": round_index,
        "seat_sampling_params": seat_sampling_params,
        "context_summary": context_summary,
        "attack_points": sorted(set(attack_points)),
        "repair_coverage": {
            "covered_key_attack_count": alignment.get("covered_key_attack_count", 0),
            "required_key_attack_count": alignment.get("required_key_attack_count", 0),
            "coverage_rate": commit_payload.get("quality_metrics", {}).get("obligation_completeness", 0.0),
            "unresolved_conflict_count": len(alignment.get("unresolved_dissents", [])),
        },
        "transfer_four_slots": {
            "source_domain_mechanism": transfer_payload.get("source_domain_mechanism"),
            "structural_mapping": transfer_payload.get("structural_mapping"),
            "breakpoints": transfer_payload.get("breakpoints"),
            "new_testable_implications": transfer_payload.get("new_testable_implications"),
        },
        "commit_decision": {
            "allowed": bool(commit_payload.get("allowed", False)),
            "decision": commit_payload.get("decision"),
            "reason": commit_payload.get("reason"),
        },
    }
    (trace_dir / "round_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (trace_dir / f"round_{round_index:04d}_round_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def run_round(payload: dict[str, Any] | None) -> dict[str, Any]:
    """API facade for one deliberation round."""

    request = RoundRunRequest.from_api_json(payload)
    final_round_input = _build_round_input(
        request.critiques,
        request.round_input,
        request.accepted_patches,
        proposed_action=request.proposed_action.strip().lower(),
    )

    default_seat_contexts = {
        seat: build_seat_context(final_round_input, seat)
        for seat in ("proposer", "critic_a", "critic_b", "repairer", "transfer_seat")
    }
    seat_contexts = {**default_seat_contexts, **request.seat_contexts}
    for seat in ("proposer", "critic_a", "critic_b", "repairer", "transfer_seat"):
        seat_contexts.setdefault(seat, {})
        if isinstance(seat_contexts[seat], dict):
            seat_contexts[seat].setdefault("sampling", {})

    trace_dir = Path(request.session_dir) / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    round_index = _next_trace_round_index(trace_dir)

    _append_round_audit_trace(
        session_dir=request.session_dir,
        artifact_id=request.artifact_id,
        round_input=final_round_input,
        seat_contexts=seat_contexts,
    )

    result = run_micro_deliberation(
        session_dir=request.session_dir,
        artifact_id=request.artifact_id,
        arena=request.arena,
        proposed_action=request.proposed_action,
        critiques=request.critiques,
        round_input=request.round_input,
        panel_state=request.panel_state,
        accepted_patches=request.accepted_patches,
        unresolved_dissents=request.unresolved_dissents,
        unresolved_dissent_saved=request.unresolved_dissent_saved,
        perspective_audits=request.perspective_audits,
        soul_profile=request.soul_profile,
        dry_run=request.dry_run,
    )
    _write_seat_chain_traces(
        session_dir=request.session_dir,
        round_index=round_index,
        round_input=final_round_input,
        seat_contexts=seat_contexts,
    )
    report = _write_round_report(
        session_dir=request.session_dir,
        round_index=round_index,
        seat_contexts=seat_contexts,
        final_round_input=final_round_input,
        result=result,
    )

    unresolved_count = report["repair_coverage"]["unresolved_conflict_count"]
    coverage_rate = report["repair_coverage"].get("coverage_rate", 0.0)
    print(
        "summary: "
        f"allowed={report['commit_decision']['allowed']} "
        f"decision={report['commit_decision']['decision']} "
        f"reason={report['commit_decision']['reason']} "
        f"未解决冲突数={unresolved_count} "
        f"覆盖率={coverage_rate}"
    )
    return {
        "commit": result["commit"],
        "event": result["event"],
        "snapshot": result["snapshot"],
        "soul_profile": request.soul_profile,
        "round_report": report,
        "dry_run": request.dry_run,
    }


def build_continuation(payload: dict[str, Any] | None) -> dict[str, Any]:
    """API facade for continuation-pack retrieval."""

    request = ContinuationPackRequest.from_api_json(payload)
    pack = build_continuation_pack(
        request.session_dir,
        goal=request.goal,
        target_artifact_id=request.target_artifact_id,
        recent_k=request.recent_k,
        entry_budget=request.entry_budget,
    )
    return ContinuationPackResponse.from_internal(pack).to_api_json()


def read_artifact(payload: dict[str, Any] | None) -> dict[str, Any]:
    """API facade for loading one artifact version."""

    request = ArtifactReadRequest.from_api_json(payload)
    return load_artifact_version(
        request.session_dir,
        artifact_id=request.artifact_id,
        version=request.version,
    )


def export_manuscript(payload: dict[str, Any] | None) -> dict[str, Any]:
    """API facade for manuscript skeleton export."""

    request = ManuscriptExportRequest.from_api_json(payload)
    return export_manuscript_skeleton(
        request.session_dir,
        artifact_id=request.artifact_id,
    )
