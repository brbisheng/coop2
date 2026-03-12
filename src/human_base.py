"""HumanBase profile primitives."""

from __future__ import annotations

from dataclasses import dataclass, field


HUMAN_BASE_SUBVALVES = (
    "practical_friction",
    "social_interpretation",
    "bounded_attention",
    "execution_realism",
)


class HumanBaseValidationError(ValueError):
    """Raised when a HumanBase profile fails validation."""


@dataclass(slots=True)
class HumanBaseProfile:
    """Baseline human-layer reasoning profile."""

    weight: float
    subvalves: dict[str, float] = field(default_factory=dict)
    heuristics: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.weight, (int, float)):
            raise HumanBaseValidationError("weight must be numeric")
        self.weight = float(self.weight)
        if not (0 < self.weight <= 1):
            raise HumanBaseValidationError("weight must be in (0, 1]")

        cleaned_subvalves: dict[str, float] = {}
        for key, value in self.subvalves.items():
            valve_name = str(key).strip().lower()
            if valve_name not in HUMAN_BASE_SUBVALVES:
                raise HumanBaseValidationError(f"unknown subvalve: {key}")
            if not isinstance(value, (int, float)):
                raise HumanBaseValidationError("subvalve weights must be numeric")
            valve_weight = float(value)
            if not (0 <= valve_weight <= 1):
                raise HumanBaseValidationError("subvalve weights must be in [0, 1]")
            cleaned_subvalves[valve_name] = valve_weight
        self.subvalves = cleaned_subvalves

        if any(not isinstance(item, str) or not item.strip() for item in self.heuristics):
            raise HumanBaseValidationError("heuristics must contain non-empty strings")


def default_human_base(weight: float = 0.45) -> HumanBaseProfile:
    """Build a default HumanBase profile for agent composition."""

    return HumanBaseProfile(
        weight=weight,
        heuristics=[
            "people get tired",
            "time and money are limited",
            "communication is often misunderstood",
            "implementation is messier than theory",
            "risk aversion affects behavior",
        ],
    )
