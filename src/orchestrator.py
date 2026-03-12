"""Seat-oriented orchestration defaults for multi-seat debate sampling."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

REQUIRED_SAMPLING_KEYS = (
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
    "max_tokens",
)

SEAT_SAMPLING_CONFIG: dict[str, dict[str, Any]] = {
    # 发散探索：更高温度
    "proposer": {
        "temperature": 1.05,
        "top_p": 0.95,
        "presence_penalty": 0.25,
        "frequency_penalty": 0.2,
        "max_tokens": 900,
    },
    # 保守审查：低温度
    "critic_a": {
        "temperature": 0.35,
        "top_p": 0.85,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.1,
        "max_tokens": 700,
    },
    # 反例挖掘：中温 + 更高 presence_penalty
    "critic_b": {
        "temperature": 0.65,
        "top_p": 0.9,
        "presence_penalty": 0.75,
        "frequency_penalty": 0.25,
        "max_tokens": 800,
    },
    # 收敛修复：中低温
    "repairer": {
        "temperature": 0.5,
        "top_p": 0.88,
        "presence_penalty": 0.1,
        "frequency_penalty": 0.2,
        "max_tokens": 750,
    },
    # 结构映射：中等温度
    "transfer_seat": {
        "temperature": 0.6,
        "top_p": 0.9,
        "presence_penalty": 0.15,
        "frequency_penalty": 0.15,
        "max_tokens": 850,
    },
}

SEAT_PROMPT_TEMPLATE: dict[str, dict[str, Any]] = {
    "proposer": {
        "objective": "最大化新颖性 + 可检验性：给出至少一个可被反驳/验证的核心预测。",
        "failure_condition": "若只复述历史观点、没有可检验预测或无法定位验证信号，则失败。",
        "focus": ["novelty", "testability", "falsifiable prediction"],
    },
    "critic_a": {
        "objective": "识别会推翻结论的脆弱点，优先给出能导致结论失效的关键前提断裂。",
        "failure_condition": "若攻击点与已存在攻击点重复（路径或标签重合）或仅作泛泛质疑，则失败。",
        "focus": ["fragility", "falsification path", "critical assumption break"],
    },
    "critic_b": {
        "objective": "寻找与 critic_a 不同路径的反证，提供独立的证据链或机制链。",
        "failure_condition": "若与 critic_a 在攻击路径/标签高度重叠，或只是换措辞重复 critic_a，则失败。",
        "focus": ["independent counterexample", "distinct reasoning path", "alternative evidence"],
    },
    "repairer": {
        "objective": "以最小修改修复最多漏洞，明确每个修改覆盖的漏洞集合。",
        "failure_condition": "若修改规模过大、未说明覆盖漏洞，或新增复杂度超过修复收益，则失败。",
        "focus": ["minimal change", "max vulnerability coverage", "tradeoff transparency"],
    },
    "transfer_seat": {
        "objective": "执行结构迁移而非修辞类比，保持因果/约束结构在新域可映射。",
        "failure_condition": "若仅给出修辞比喻、未保留关键结构同构关系，则失败。",
        "focus": ["structural mapping", "constraint preservation", "causal isomorphism"],
    },
}


def get_sampling_config_for_seat(seat: str) -> dict[str, Any]:
    """Return a defensive copy of sampling config for one seat."""

    seat_key = str(seat).strip().lower()
    if seat_key not in SEAT_SAMPLING_CONFIG:
        supported = ", ".join(sorted(SEAT_SAMPLING_CONFIG))
        raise ValueError(f"Unsupported seat '{seat}'. Supported seats: {supported}")

    config = deepcopy(SEAT_SAMPLING_CONFIG[seat_key])
    for required in REQUIRED_SAMPLING_KEYS:
        if required not in config:
            raise ValueError(f"Sampling config for seat '{seat_key}' missing required key: {required}")
    return config


def get_prompt_template_for_seat(seat: str) -> dict[str, Any]:
    """Return a defensive copy of seat prompt contract."""

    seat_key = str(seat).strip().lower()
    if seat_key not in SEAT_PROMPT_TEMPLATE:
        supported = ", ".join(sorted(SEAT_PROMPT_TEMPLATE))
        raise ValueError(f"Unsupported seat '{seat}'. Supported seats: {supported}")
    return deepcopy(SEAT_PROMPT_TEMPLATE[seat_key])


def build_seat_instruction_message(seat: str, seat_context: dict[str, Any]) -> dict[str, str]:
    """Build system message that makes seat objective/failure contract explicit."""

    seat_key = str(seat).strip().lower()
    template = get_prompt_template_for_seat(seat_key)
    context_keys = sorted(k for k, v in seat_context.items() if v not in (None, {}, []))
    return {
        "role": "system",
        "content": (
            f"你当前 seat: {seat_key}\n"
            f"目标函数: {template['objective']}\n"
            f"失败条件: {template['failure_condition']}\n"
            f"重点检查: {', '.join(template['focus'])}\n"
            f"可用上下文字段: {', '.join(context_keys) if context_keys else 'none'}\n"
            "输出请显式说明你的攻击/修复/迁移路径，避免与已有路径重复。"
        ),
    }


def build_retry_correction_message(reasons: list[str]) -> dict[str, str]:
    """Build retry correction message with explicit repeat/failure hints."""

    normalized = [str(reason).strip() for reason in reasons if str(reason).strip()]
    hint = "；".join(normalized) if normalized else "你的输出未满足 seat 约束"
    return {
        "role": "user",
        "content": f"你重复了/违反了以下约束：{hint}。请修正并只做一次高质量重试。",
    }


def _normalize_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, ensure_ascii=False)
    return str(payload)


def _extract_tags(payload: str, keys: tuple[str, ...]) -> set[str]:
    lowered = payload.lower()
    tags: set[str] = set()
    for key in keys:
        pattern = rf'"{re.escape(key)}"\s*:\s*\[(.*?)\]'
        match = re.search(pattern, lowered)
        if not match:
            continue
        values = [item.strip().strip('"\' ') for item in match.group(1).split(",") if item.strip()]
        tags.update(value for value in values if value)
    return tags


def _normalize_list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple, set)):
        normalized: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized
    return []


def _extract_attack_tokens(item: dict[str, Any]) -> set[str]:
    if not isinstance(item, dict):
        return set()

    token_fields = (
        "attack_labels",
        "challenged_fields",
        "reasoning_path_labels",
        "flip_condition",
        "evidence_refs",
    )
    tokens: set[str] = set()
    for key in token_fields:
        for value in _normalize_list_field(item.get(key)):
            token = value.strip().lower()
            if token:
                tokens.add(token)
    return tokens


def validate_attack_response_alignment(
    *,
    critiques: list[dict[str, Any]],
    repair_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate whether repair output aligns with critique attacks.

    Rules:
    1) when two independent critiques exist, repair must cover at least one key attack point;
    2) uncovered attacks must be present in `not_addressed_attacks` and be convertible to unresolved dissent.
    """

    normalized_repair = dict(repair_output) if isinstance(repair_output, dict) else {}
    addressed = normalized_repair.get("addressed_attacks")
    not_addressed = normalized_repair.get("not_addressed_attacks")
    addressed_items = [item for item in (addressed or []) if isinstance(item, dict)]
    not_addressed_items = [item for item in (not_addressed or []) if isinstance(item, dict)]

    independent_critiques = [item for item in critiques if isinstance(item, dict)][:2]
    key_attacks: list[dict[str, Any]] = independent_critiques if len(independent_critiques) >= 2 else []

    addressed_tokens: set[str] = set()
    for item in addressed_items:
        addressed_tokens.update(_extract_attack_tokens(item))

    covered_count = 0
    uncovered_from_critique: list[dict[str, Any]] = []
    for critique in key_attacks:
        attack_tokens = _extract_attack_tokens(critique)
        if attack_tokens and attack_tokens & addressed_tokens:
            covered_count += 1
        else:
            uncovered_from_critique.append(critique)

    not_addressed_tokens: set[str] = set()
    for item in not_addressed_items:
        not_addressed_tokens.update(_extract_attack_tokens(item))

    unresolved_dissents: list[dict[str, Any]] = []
    for idx, critique in enumerate(uncovered_from_critique, start=1):
        unresolved_dissents.append(
            {
                "dissent_id": f"auto-unresolved-{idx}",
                "status": "open",
                "conflict_type": "execution",
                "message": "repair did not address this critique attack",
                "attack": critique,
            }
        )

    missing_not_addressed = any(
        _extract_attack_tokens(critique) - not_addressed_tokens for critique in uncovered_from_critique
    )

    aligned = True
    reasons: list[str] = []
    if key_attacks and covered_count < 1:
        aligned = False
        reasons.append("repair must cover at least one key point from independent critiques")
    if uncovered_from_critique and missing_not_addressed:
        aligned = False
        reasons.append("uncovered attacks must appear in not_addressed_attacks")

    return {
        "is_aligned": aligned,
        "covered_key_attack_count": covered_count,
        "required_key_attack_count": 1 if key_attacks else 0,
        "uncovered_attacks": uncovered_from_critique,
        "unresolved_dissents": unresolved_dissents,
        "reasons": reasons,
    }


def _parse_json_object(text: str) -> dict[str, Any] | None:
    stripped = str(text).strip()
    if not stripped.startswith("{"):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def validate_transfer_payload(output_text: str) -> tuple[bool, list[str], dict[str, Any] | None]:
    """Validate transfer seat output follows the strict 4-slot payload."""

    parsed = _parse_json_object(output_text)
    required_keys = (
        "source_domain_mechanism",
        "structural_mapping",
        "breakpoints",
        "new_testable_implications",
    )
    reasons: list[str] = []
    if not parsed:
        return False, ["transfer 输出必须是 JSON 对象，且包含严格四格"], None

    for key in required_keys:
        if key not in parsed:
            reasons.append(f"缺少字段: {key}")

    extras = [key for key in parsed if key not in required_keys]
    if extras:
        reasons.append(f"仅允许四格字段，存在额外字段: {', '.join(extras)}")

    for key in required_keys:
        value = parsed.get(key)
        if value in (None, "", [], {}):
            reasons.append(f"字段不能为空: {key}")

    return len(reasons) == 0, reasons, parsed


def validate_seat_output(
    *,
    seat: str,
    output_text: str,
    seat_context: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """Run local seat-specific validation; return (is_valid, reasons)."""

    seat_key = str(seat).strip().lower()
    text = _normalize_text(output_text).lower()
    context = seat_context if isinstance(seat_context, dict) else {}
    reasons: list[str] = []

    if seat_key == "proposer":
        novelty_markers = ("新颖", "novel", "新假设", "new mechanism")
        testability_markers = ("可检验", "test", "falsif", "预测", "prediction")
        if not any(marker in text for marker in novelty_markers):
            reasons.append("缺少新颖性声明")
        if not any(marker in text for marker in testability_markers):
            reasons.append("缺少可检验/可反驳预测")

    elif seat_key == "critic_a":
        parsed = _parse_json_object(output_text)
        required_keys = (
            "attack_labels",
            "challenged_fields",
            "reasoning_path_labels",
            "flip_condition",
            "evidence_refs",
        )
        if not parsed:
            reasons.append("critic 输出必须是包含统一字段的 JSON 对象")
        else:
            for key in required_keys:
                if key not in parsed:
                    reasons.append(f"缺少字段: {key}")
        fragile_markers = ("脆弱", "fragile", "推翻", "invalidate", "break")
        if not any(marker in text for marker in fragile_markers):
            reasons.append("未识别可推翻结论的脆弱点")
        prior = _normalize_text(context.get("critique_b", ""))
        if prior and len(set(text.split()) & set(prior.lower().split())) > 15:
            reasons.append("与已有攻击点高度重复")

    elif seat_key == "critic_b":
        parsed = _parse_json_object(output_text)
        required_keys = (
            "attack_labels",
            "challenged_fields",
            "reasoning_path_labels",
            "flip_condition",
            "evidence_refs",
        )
        if not parsed:
            reasons.append("critic 输出必须是包含统一字段的 JSON 对象")
        else:
            for key in required_keys:
                if key not in parsed:
                    reasons.append(f"缺少字段: {key}")
        alternative_markers = ("不同路径", "independent", "alternative", "另一条")
        if not any(marker in text for marker in alternative_markers):
            reasons.append("未明确与critic_a不同路径")
        critique_a = _normalize_text(context.get("critique_a", ""))
        if critique_a and len(set(text.split()) & set(critique_a.lower().split())) > 18:
            reasons.append("与critic_a路径重复")

    elif seat_key == "repairer":
        parsed = _parse_json_object(output_text)
        required_keys = (
            "addressed_attacks",
            "not_addressed_attacks",
            "patch",
            "new_testable_implication",
        )
        if not parsed:
            reasons.append("repair 输出必须是包含统一字段的 JSON 对象")
        else:
            for key in required_keys:
                if key not in parsed:
                    reasons.append(f"缺少字段: {key}")
        minimal_markers = ("最小", "minimal", "小改", "least change")
        coverage_markers = ("覆盖", "cover", "漏洞", "vulnerability", "risk")
        if not any(marker in text for marker in minimal_markers):
            reasons.append("未说明最小修改原则")
        if not any(marker in text for marker in coverage_markers):
            reasons.append("未说明修复覆盖的漏洞")

        transfer_breakpoints = _normalize_list_field(context.get("transfer_breakpoints"))
        if transfer_breakpoints and parsed:
            output_compact = json.dumps(parsed, ensure_ascii=False).lower()
            missing_breakpoints = [bp for bp in transfer_breakpoints if bp.lower() not in output_compact]
            if missing_breakpoints:
                reasons.append(
                    "repair 必须逐条回应 transfer breakpoints，缺失: " + ", ".join(missing_breakpoints)
                )

    elif seat_key == "transfer_seat":
        transfer_ok, transfer_reasons, _ = validate_transfer_payload(output_text)
        if not transfer_ok:
            reasons.extend(transfer_reasons)

        structure_markers = ("结构", "structure", "约束", "constraint", "causal")
        rhetorical_markers = ("像", "好比", "就像", "metaphor")
        if not any(marker in text for marker in structure_markers):
            reasons.append("未给出结构迁移")
        if any(marker in text for marker in rhetorical_markers) and "结构" not in text and "structure" not in text:
            reasons.append("出现修辞类比但缺少结构同构")

    return len(reasons) == 0, reasons


def build_seat_context(round_state: dict[str, Any], seat: str) -> dict[str, Any]:
    """Build seat-scoped context window from one round state payload."""

    if not isinstance(round_state, dict):
        raise ValueError("round_state must be a dict")

    seat_key = str(seat).strip().lower()
    if seat_key not in SEAT_SAMPLING_CONFIG:
        supported = ", ".join(sorted(SEAT_SAMPLING_CONFIG))
        raise ValueError(f"Unsupported seat '{seat}'. Supported seats: {supported}")

    proposal = round_state.get("proposal")
    critique_a = round_state.get("critique_a")
    critique_b = round_state.get("critique_b")
    transfer = round_state.get("transfer")
    transfer_breakpoints = _normalize_list_field(transfer.get("breakpoints")) if isinstance(transfer, dict) else []

    one_critique = critique_a if critique_a not in (None, {}, []) else critique_b

    seat_view: dict[str, Any]
    if seat_key == "proposer":
        seat_view = {
            "topic": round_state.get("topic"),
            "history_summary": round_state.get("history_summary"),
        }
    elif seat_key == "critic_a":
        seat_view = {
            "proposal": proposal,
            "minimal_evidence": round_state.get("minimal_evidence"),
            "critique_b": critique_b,
        }
    elif seat_key == "critic_b":
        seat_view = {
            "proposal": proposal,
            "critique_a": critique_a,
        }
    elif seat_key == "repairer":
        seat_view = {
            "proposal": proposal,
            "critique_a": critique_a,
            "critique_b": critique_b,
            "transfer": transfer,
            "transfer_breakpoints": transfer_breakpoints,
        }
    else:  # transfer_seat
        seat_view = {
            "proposal": proposal,
            "critique": one_critique,
        }

    # Keep absent values out of the context window payload.
    return {key: value for key, value in seat_view.items() if value not in (None, {}, [])}
