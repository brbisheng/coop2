"""HumanBase profile primitives."""

from __future__ import annotations

from dataclasses import dataclass, field


class HumanBaseValidationError(ValueError):
    """Raised when a HumanBase profile fails validation."""


@dataclass(slots=True)
class HumanBaseProfile:
    """Baseline human-layer reasoning profile."""

    weight: float
    heuristics: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.weight, (int, float)):
            raise HumanBaseValidationError("weight must be numeric")
        self.weight = float(self.weight)
        if not (0 < self.weight <= 1):
            raise HumanBaseValidationError("weight must be in (0, 1]")

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
