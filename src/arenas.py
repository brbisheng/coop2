"""Arena configuration primitives and loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


class ArenaConfigError(ValueError):
    """Raised when arena config fails validation."""


@dataclass(slots=True)
class ArenaSpec:
    arena_name: str
    accepted_artifact_types: list[str]
    required_obligations: dict[str, int]
    min_unique_agents: int
    allowed_outputs: list[str]

    def __post_init__(self) -> None:
        if not self.arena_name:
            raise ArenaConfigError("arena_name is required")
        if self.min_unique_agents < 3:
            raise ArenaConfigError("min_unique_agents must be >= 3")

        critiques = int(self.required_obligations.get("independent_critiques", 0))
        if critiques < 2:
            raise ArenaConfigError("required_obligations.independent_critiques must be >= 2")


def _load_yaml_like(path: str | Path) -> dict[str, Any]:
    """Load config authored in YAML-compatible JSON subset."""

    text = Path(path).read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ArenaConfigError(
            "Config parsing failed. Use JSON syntax in .yaml files for this MVP loader."
        ) from exc

    if not isinstance(payload, dict):
        raise ArenaConfigError("arena config root must be an object")
    return payload


def load_arenas(path: str | Path) -> dict[str, ArenaSpec]:
    raw = _load_yaml_like(path)
    items = raw.get("arenas", [])
    if not isinstance(items, list):
        raise ArenaConfigError("arenas must be a list")

    specs: dict[str, ArenaSpec] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ArenaConfigError("each arena item must be an object")
        spec = ArenaSpec(
            arena_name=str(item.get("arena_name", "")).strip(),
            accepted_artifact_types=list(item.get("accepted_artifact_types", [])),
            required_obligations=dict(item.get("required_obligations", {})),
            min_unique_agents=int(item.get("min_unique_agents", 0)),
            allowed_outputs=list(item.get("allowed_outputs", [])),
        )
        specs[spec.arena_name] = spec

    return specs
