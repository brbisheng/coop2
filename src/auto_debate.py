"""Automated multi-seat debate runner wired to service_api contracts."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .llm_client import OpenRouterClient
from .orchestrator import build_seat_context
from .service_api import build_continuation, read_artifact, run_round

SEAT_ORDER = ("proposer", "critic_a", "critic_b", "transfer_seat", "repairer")


@dataclass(slots=True)
class AutoDebateConfig:
    topic: str
    api_key: str
    model: str
    rounds: int
    session_dir: Path
    artifact_id: str = "artifact_main"
    arena: str = "mechanism"


def _extract_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    first_choice = choices[0] if isinstance(choices, list) and choices else {}
    message = first_choice.get("message") if isinstance(first_choice, dict) else {}
    return str(message.get("content", "") if isinstance(message, dict) else "")


def _parse_json_object(text: str) -> dict[str, Any] | None:
    stripped = str(text).strip()
    if not stripped:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _default_payload_for_seat(seat: str, *, topic: str, critique_a: dict[str, Any] | None = None) -> dict[str, Any]:
    if seat == "proposer":
        return {
            "hypothesis": f"{topic} 的核心机制假设",
            "mechanism": "提出可证伪的因果机制",
            "prediction": "若机制成立，关键观测指标将出现方向性变化",
        }
    if seat in {"critic_a", "critic_b"}:
        return {
            "attack_labels": [f"{seat}-attack"],
            "challenged_fields": ["mechanism"],
            "reasoning_path_labels": [f"{seat}-path"],
            "flip_condition": "出现与预测相反的关键证据",
            "evidence_refs": ["to-be-collected"],
            "summary": "关键前提可能被反例击穿",
        }
    if seat == "transfer_seat":
        return {
            "source_domain_mechanism": "原域机制的关键约束",
            "structural_mapping": "目标域保留同构约束关系",
            "breakpoints": ["约束映射可能失效"],
            "new_testable_implications": "目标域中的可测预测",
        }
    if seat == "repairer":
        addressed = [critique_a] if isinstance(critique_a, dict) else []
        return {
            "addressed_attacks": addressed,
            "not_addressed_attacks": [],
            "patch": {"mechanism": "收缩适用范围并增加识别条件"},
            "new_testable_implication": "补丁后预测在高噪声条件下更稳健",
            "responded_breakpoints": ["约束映射可能失效"],
            "summary": "最小补丁覆盖主要攻击点",
        }
    return {}


def _seat_prompt(seat: str, *, topic: str, continuation: dict[str, Any], artifact: dict[str, Any], round_index: int) -> str:
    schema_hint = {
        "proposer": '{"hypothesis": "...", "mechanism": "...", "prediction": "..."}',
        "critic_a": '{"attack_labels": ["..."], "challenged_fields": ["..."], "reasoning_path_labels": ["..."], "flip_condition": "...", "evidence_refs": ["..."], "summary": "..."}',
        "critic_b": '{"attack_labels": ["..."], "challenged_fields": ["..."], "reasoning_path_labels": ["..."], "flip_condition": "...", "evidence_refs": ["..."], "summary": "..."}',
        "transfer_seat": '{"source_domain_mechanism": "...", "structural_mapping": "...", "breakpoints": ["..."], "new_testable_implications": "..."}',
        "repairer": '{"addressed_attacks": [{...}], "not_addressed_attacks": [{...}], "patch": {...}, "new_testable_implication": "...", "responded_breakpoints": ["..."], "summary": "..."}',
    }
    return (
        f"topic: {topic}\n"
        f"round: {round_index}\n"
        f"continuation.minimal_context: {json.dumps(continuation.get('minimal_context', {}), ensure_ascii=False)}\n"
        f"artifact: {json.dumps(artifact, ensure_ascii=False)}\n"
        f"请仅输出 JSON 对象，不要输出解释。schema: {schema_hint[seat]}"
    )


def _resolve_session_dir(session_dir_arg: str) -> Path:
    raw = Path(session_dir_arg)
    if raw.is_absolute() or len(raw.parts) > 1:
        return raw
    return Path("data") / "sessions" / session_dir_arg


def _panel_state() -> dict[str, Any]:
    return {
        "agents": [
            {"agent_id": "auto-a", "human_base_weight": 0.5, "module_weights": {"economics": 0.6}},
            {"agent_id": "auto-b", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
            {"agent_id": "auto-c", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
        ]
    }


def run_auto_debate(config: AutoDebateConfig) -> list[dict[str, Any]]:
    config.session_dir.mkdir(parents=True, exist_ok=True)
    trace_dir = config.session_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    client = OpenRouterClient(api_key=config.api_key, model=config.model)
    results: list[dict[str, Any]] = []
    history_summary = ""

    for round_index in range(1, config.rounds + 1):
        continuation = build_continuation(
            {
                "session_dir": str(config.session_dir),
                "goal": config.topic,
                "target_artifact_id": config.artifact_id,
            }
        )
        artifact = read_artifact(
            {
                "session_dir": str(config.session_dir),
                "artifact_id": config.artifact_id,
            }
        )

        round_state: dict[str, Any] = {
            "topic": config.topic,
            "history_summary": history_summary,
            "minimal_evidence": continuation.get("minimal_context", {}).get("evidence_refs", []),
        }
        seat_outputs: dict[str, dict[str, Any]] = {}
        seat_responses: dict[str, dict[str, Any]] = {}

        for seat in SEAT_ORDER:
            response = client.run_seat(
                seat=seat,
                round_index=round_index,
                messages=[{"role": "user", "content": _seat_prompt(seat, topic=config.topic, continuation=continuation, artifact=artifact, round_index=round_index)}],
                trace_dir=trace_dir,
                round_state=round_state,
            )
            seat_responses[seat] = response
            parsed = _parse_json_object(_extract_content(response))
            seat_outputs[seat] = parsed or _default_payload_for_seat(seat, topic=config.topic, critique_a=seat_outputs.get("critic_a"))

            if seat == "proposer":
                round_state["proposal"] = seat_outputs[seat]
            elif seat in {"critic_a", "critic_b"}:
                round_state[seat] = seat_outputs[seat]
            elif seat == "transfer_seat":
                round_state["transfer"] = seat_outputs[seat]

        round_input = {
            "proposal": seat_outputs["proposer"],
            "critique_a": seat_outputs["critic_a"],
            "critique_b": seat_outputs["critic_b"],
            "transfer": seat_outputs["transfer_seat"],
            "repair": seat_outputs["repairer"],
            "decision": {"action": "commit", "rationale": "auto debate decision"},
        }
        seat_contexts = {
            seat: build_seat_context(round_input | {"topic": config.topic, "history_summary": history_summary}, seat)
            for seat in SEAT_ORDER
        }

        request_payload = {
            "session_dir": str(config.session_dir),
            "artifact_id": config.artifact_id,
            "arena": config.arena,
            "proposed_action": "commit",
            "critiques": [seat_outputs["critic_a"], seat_outputs["critic_b"]],
            "panel_state": _panel_state(),
            "round_input": round_input,
            "accepted_patches": [{"proposed_changes": seat_outputs["repairer"].get("patch", {})}],
            "unresolved_dissent_saved": True,
            "seat_contexts": seat_contexts,
            "soul_profile": {"style": {"tone": "concise"}},
        }
        result = run_round(request_payload)
        results.append(result)

        alignment = result.get("event", {}).get("attack_response_alignment", {})
        decision = result.get("commit", {})
        context_payload = {
            "topic": config.topic,
            "continuation": continuation,
            "artifact": artifact,
            "seat_contexts": seat_contexts,
            "seat_outputs": seat_outputs,
            "seat_responses": seat_responses,
        }

        prefix = f"round_{round_index:04d}"
        (trace_dir / f"{prefix}_request.json").write_text(json.dumps(request_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (trace_dir / f"{prefix}_response.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        (trace_dir / f"{prefix}_context.json").write_text(json.dumps(context_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (trace_dir / f"{prefix}_alignment.json").write_text(json.dumps(alignment, ensure_ascii=False, indent=2), encoding="utf-8")
        (trace_dir / f"{prefix}_decision.json").write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8")

        history_summary = (
            f"round={round_index}; allowed={decision.get('allowed')}; "
            f"decision={decision.get('decision')}; unresolved={len(alignment.get('unresolved_dissents', []))}"
        )
        print(
            "auto-round summary:",
            f"round={round_index}",
            f"decision={decision.get('decision')}",
            f"allowed={decision.get('allowed')}",
            f"reason={decision.get('reason')}",
        )

    return results


def _parse_args(argv: list[str] | None = None) -> AutoDebateConfig:
    parser = argparse.ArgumentParser(description="Run automated debate rounds with OpenRouter seats.")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--api-key", default=os.getenv("OPENROUTER_API_KEY", ""))
    parser.add_argument("--model", required=True)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--session-dir", required=True)
    parser.add_argument("--artifact-id", default="artifact_main")
    parser.add_argument("--arena", default="mechanism")

    args = parser.parse_args(argv)
    if not args.api_key:
        raise SystemExit("Missing OpenRouter API key: pass --api-key or set OPENROUTER_API_KEY")
    if args.rounds < 1:
        raise SystemExit("--rounds must be >= 1")

    return AutoDebateConfig(
        topic=str(args.topic),
        api_key=str(args.api_key),
        model=str(args.model),
        rounds=int(args.rounds),
        session_dir=_resolve_session_dir(str(args.session_dir)),
        artifact_id=str(args.artifact_id),
        arena=str(args.arena),
    )


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)
    run_auto_debate(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
