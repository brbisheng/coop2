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
