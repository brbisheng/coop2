"""Unified data models for artifacts, patches, debates, commits, and snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .protocol import (
    CURRENT_SCHEMA_VERSION,
    ArtifactStatus,
    CommitStatus,
    DebateArena,
    DebateDecision,
    ModelValidationError,
    parse_enum,
)


@dataclass(slots=True)
class ArtifactCard:
    artifact_id: str
    title: str
    content: str
    status: ArtifactStatus | str
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self._require_non_empty("artifact_id", self.artifact_id)
        self._require_non_empty("title", self.title)
        self._require_non_empty("content", self.content)
        self.status = parse_enum(str(self.status), ArtifactStatus, "status")
        if self.author is not None and not isinstance(self.author, str):
            raise ModelValidationError("author must be str | None")
        if any(not isinstance(tag, str) or not tag.strip() for tag in self.tags):
            raise ModelValidationError("tags must be non-empty strings")
        self._validate_schema_version()

    def _validate_schema_version(self) -> None:
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ModelValidationError("schema_version must be a positive integer")

    @staticmethod
    def _require_non_empty(name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ModelValidationError(f"{name} must be a non-empty string")


@dataclass(slots=True)
class DeltaPatch:
    patch_id: str
    target_artifact_id: str
    diff: str
    proposer: str
    rationale: str | None = None
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self._require_non_empty("patch_id", self.patch_id)
        self._require_non_empty("target_artifact_id", self.target_artifact_id)
        self._require_non_empty("diff", self.diff)
        self._require_non_empty("proposer", self.proposer)
        if self.rationale is not None and not isinstance(self.rationale, str):
            raise ModelValidationError("rationale must be str | None")
        self._validate_schema_version()

    def _validate_schema_version(self) -> None:
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ModelValidationError("schema_version must be a positive integer")

    @staticmethod
    def _require_non_empty(name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ModelValidationError(f"{name} must be a non-empty string")


@dataclass(slots=True)
class DebateTurn:
    turn_id: str
    arena: DebateArena | str
    decision: DebateDecision | str
    message: str
    accepted_patch_ids: list[str] = field(default_factory=list)
    speaker: str | None = None
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self._require_non_empty("turn_id", self.turn_id)
        self.arena = parse_enum(str(self.arena), DebateArena, "arena")
        self.decision = parse_enum(str(self.decision), DebateDecision, "decision")
        self._require_non_empty("message", self.message)
        if self.speaker is not None and not isinstance(self.speaker, str):
            raise ModelValidationError("speaker must be str | None")
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.accepted_patch_ids):
            raise ModelValidationError("accepted_patch_ids must contain non-empty strings")
        self._validate_schema_version()

    def _validate_schema_version(self) -> None:
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ModelValidationError("schema_version must be a positive integer")

    @staticmethod
    def _require_non_empty(name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ModelValidationError(f"{name} must be a non-empty string")


@dataclass(slots=True)
class CommitRecord:
    commit_id: str
    patch_ids: list[str]
    status: CommitStatus | str
    message: str | None = None
    created_at: str | None = None
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self._require_non_empty("commit_id", self.commit_id)
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.patch_ids):
            raise ModelValidationError("patch_ids must contain non-empty strings")
        self.status = parse_enum(str(self.status), CommitStatus, "status")
        if self.message is not None and not isinstance(self.message, str):
            raise ModelValidationError("message must be str | None")
        if self.created_at is not None and not isinstance(self.created_at, str):
            raise ModelValidationError("created_at must be str | None")
        self._validate_schema_version()

    def _validate_schema_version(self) -> None:
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ModelValidationError("schema_version must be a positive integer")

    @staticmethod
    def _require_non_empty(name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ModelValidationError(f"{name} must be a non-empty string")


@dataclass(slots=True)
class Snapshot:
    snapshot_id: str
    artifacts: list[ArtifactCard] = field(default_factory=list)
    patches: list[DeltaPatch] = field(default_factory=list)
    debate_turns: list[DebateTurn] = field(default_factory=list)
    commits: list[CommitRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self._require_non_empty("snapshot_id", self.snapshot_id)
        if not isinstance(self.metadata, dict):
            raise ModelValidationError("metadata must be dict[str, Any]")
        self._validate_schema_version()
        self.validate_references()

    def validate_references(self) -> None:
        artifact_ids = {artifact.artifact_id for artifact in self.artifacts}
        patch_ids = {patch.patch_id for patch in self.patches}

        for patch in self.patches:
            if patch.target_artifact_id not in artifact_ids:
                raise ModelValidationError(
                    f"patch target must exist: patch={patch.patch_id}, "
                    f"target_artifact_id={patch.target_artifact_id}"
                )

        for turn in self.debate_turns:
            missing = [pid for pid in turn.accepted_patch_ids if pid not in patch_ids]
            if missing:
                raise ModelValidationError(
                    f"accepted_patch_ids must resolve to known patches: "
                    f"turn={turn.turn_id}, missing={missing}"
                )

        for commit in self.commits:
            missing = [pid for pid in commit.patch_ids if pid not in patch_ids]
            if missing:
                raise ModelValidationError(
                    f"commit.patch_ids must resolve to known patches: "
                    f"commit={commit.commit_id}, missing={missing}"
                )

    def _validate_schema_version(self) -> None:
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ModelValidationError("schema_version must be a positive integer")

    @staticmethod
    def _require_non_empty(name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ModelValidationError(f"{name} must be a non-empty string")
