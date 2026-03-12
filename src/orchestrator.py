"""Seat-oriented orchestration defaults for multi-seat debate sampling."""

from __future__ import annotations

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
        }
    else:  # transfer_seat
        seat_view = {
            "proposal": proposal,
            "critique": one_critique,
        }

    # Keep absent values out of the context window payload.
    return {key: value for key, value in seat_view.items() if value not in (None, {}, [])}
