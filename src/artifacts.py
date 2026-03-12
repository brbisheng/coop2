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


CONFLICT_TYPE_VALUES = (
    "definition",
    "mechanism",
    "evidence",
    "measurement",
    "scope",
    "policy",
    "execution",
)


def normalize_conflict_type(value: Any) -> str:
    """Validate and normalize dissent conflict type."""

    normalized = str(value or "").strip().lower()
    if normalized not in CONFLICT_TYPE_VALUES:
        allowed = "/".join(CONFLICT_TYPE_VALUES)
        raise ModelValidationError(
            f"Invalid value for 'conflict_type': {value!r}. Allowed: {allowed}."
        )
    return normalized


@dataclass(slots=True)
class ArtifactCard:
    artifact_id: str
    title: str
    content: str
    status: ArtifactStatus | str
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    parent_ids: list[str] | None = None
    version: str | None = None
    open_issues: list[str] | None = None
    proposed_changes: dict[str, Any] | None = None
    reasons: str | None = None
    dissent_patch_ids: list[str] | None = None
    why_not_others: str | None = None
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
        self._validate_traceability_fields()
        self._validate_schema_version()

    def _validate_traceability_fields(self) -> None:
        if self.parent_ids is None:
            raise ModelValidationError("parent_ids is required")
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.parent_ids):
            raise ModelValidationError("parent_ids must contain non-empty strings")
        if self.version is None:
            raise ModelValidationError("version is required")
        self._require_non_empty("version", self.version)
        if self.open_issues is None:
            raise ModelValidationError("open_issues is required")
        if any(not isinstance(issue, str) or not issue.strip() for issue in self.open_issues):
            raise ModelValidationError("open_issues must contain non-empty strings")
        if self.proposed_changes is None:
            raise ModelValidationError("proposed_changes is required")
        if not isinstance(self.proposed_changes, dict):
            raise ModelValidationError("proposed_changes must be dict[str, Any]")
        if self.reasons is None:
            raise ModelValidationError("reasons is required")
        self._require_non_empty("reasons", self.reasons)
        if self.dissent_patch_ids is None:
            raise ModelValidationError("dissent_patch_ids is required")
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.dissent_patch_ids):
            raise ModelValidationError("dissent_patch_ids must contain non-empty strings")
        if self.why_not_others is None:
            raise ModelValidationError("why_not_others is required")
        self._require_non_empty("why_not_others", self.why_not_others)

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
    parent_ids: list[str] | None = None
    version: str | None = None
    open_issues: list[str] | None = None
    proposed_changes: dict[str, Any] | None = None
    reasons: str | None = None
    dissent_patch_ids: list[str] | None = None
    why_not_others: str | None = None
    rationale: str | None = None
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self._require_non_empty("patch_id", self.patch_id)
        self._require_non_empty("target_artifact_id", self.target_artifact_id)
        self._require_non_empty("diff", self.diff)
        self._require_non_empty("proposer", self.proposer)
        self._validate_traceability_fields()
        if self.rationale is not None and not isinstance(self.rationale, str):
            raise ModelValidationError("rationale must be str | None")
        self._validate_schema_version()

    def _validate_traceability_fields(self) -> None:
        if self.parent_ids is None:
            raise ModelValidationError("parent_ids is required")
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.parent_ids):
            raise ModelValidationError("parent_ids must contain non-empty strings")
        if self.version is None:
            raise ModelValidationError("version is required")
        self._require_non_empty("version", self.version)
        if self.open_issues is None:
            raise ModelValidationError("open_issues is required")
        if any(not isinstance(issue, str) or not issue.strip() for issue in self.open_issues):
            raise ModelValidationError("open_issues must contain non-empty strings")
        if self.proposed_changes is None:
            raise ModelValidationError("proposed_changes is required")
        if not isinstance(self.proposed_changes, dict):
            raise ModelValidationError("proposed_changes must be dict[str, Any]")
        if self.reasons is None:
            raise ModelValidationError("reasons is required")
        self._require_non_empty("reasons", self.reasons)
        if self.dissent_patch_ids is None:
            raise ModelValidationError("dissent_patch_ids is required")
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.dissent_patch_ids):
            raise ModelValidationError("dissent_patch_ids must contain non-empty strings")
        if self.why_not_others is None:
            raise ModelValidationError("why_not_others is required")
        self._require_non_empty("why_not_others", self.why_not_others)

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
    parent_ids: list[str] | None = None
    version: str | None = None
    open_issues: list[str] | None = None
    proposed_changes: dict[str, Any] | None = None
    reasons: str | None = None
    dissent_patch_ids: list[str] | None = None
    why_not_others: str | None = None
    message: str | None = None
    created_at: str | None = None
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self._require_non_empty("commit_id", self.commit_id)
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.patch_ids):
            raise ModelValidationError("patch_ids must contain non-empty strings")
        self.status = parse_enum(str(self.status), CommitStatus, "status")
        self._validate_traceability_fields()
        if self.message is not None and not isinstance(self.message, str):
            raise ModelValidationError("message must be str | None")
        if self.created_at is not None and not isinstance(self.created_at, str):
            raise ModelValidationError("created_at must be str | None")
        self._validate_schema_version()

    def _validate_schema_version(self) -> None:
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ModelValidationError("schema_version must be a positive integer")

    def _validate_traceability_fields(self) -> None:
        if self.parent_ids is None:
            raise ModelValidationError("parent_ids is required")
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.parent_ids):
            raise ModelValidationError("parent_ids must contain non-empty strings")
        if self.version is None:
            raise ModelValidationError("version is required")
        self._require_non_empty("version", self.version)
        if self.open_issues is None:
            raise ModelValidationError("open_issues is required")
        if any(not isinstance(issue, str) or not issue.strip() for issue in self.open_issues):
            raise ModelValidationError("open_issues must contain non-empty strings")
        if self.proposed_changes is None:
            raise ModelValidationError("proposed_changes is required")
        if not isinstance(self.proposed_changes, dict):
            raise ModelValidationError("proposed_changes must be dict[str, Any]")
        if self.reasons is None:
            raise ModelValidationError("reasons is required")
        self._require_non_empty("reasons", self.reasons)
        if self.dissent_patch_ids is None:
            raise ModelValidationError("dissent_patch_ids is required")
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.dissent_patch_ids):
            raise ModelValidationError("dissent_patch_ids must contain non-empty strings")
        if self.why_not_others is None:
            raise ModelValidationError("why_not_others is required")
        self._require_non_empty("why_not_others", self.why_not_others)

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
    parent_ids: list[str] | None = None
    version: str | None = None
    open_issues: list[dict[str, Any]] | None = None
    proposed_changes: list[dict[str, Any]] | None = None
    reasons: list[str] | None = None
    dissent_patch_ids: list[str] | None = None
    why_not_others: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self._require_non_empty("snapshot_id", self.snapshot_id)
        if not isinstance(self.metadata, dict):
            raise ModelValidationError("metadata must be dict[str, Any]")
        self._validate_traceability_fields()
        self._validate_schema_version()
        self.validate_references()

    def _validate_traceability_fields(self) -> None:
        if self.parent_ids is None:
            raise ModelValidationError("parent_ids is required")
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.parent_ids):
            raise ModelValidationError("parent_ids must contain non-empty strings")
        if self.version is None:
            raise ModelValidationError("version is required")
        self._require_non_empty("version", self.version)
        if self.open_issues is None:
            raise ModelValidationError("open_issues is required")
        if any(not isinstance(issue, dict) for issue in self.open_issues):
            raise ModelValidationError("open_issues must contain dict items")
        if self.proposed_changes is None:
            raise ModelValidationError("proposed_changes is required")
        if any(not isinstance(change, dict) for change in self.proposed_changes):
            raise ModelValidationError("proposed_changes must contain dict items")
        if self.reasons is None:
            raise ModelValidationError("reasons is required")
        if any(not isinstance(reason, str) or not reason.strip() for reason in self.reasons):
            raise ModelValidationError("reasons must contain non-empty strings")
        if self.dissent_patch_ids is None:
            raise ModelValidationError("dissent_patch_ids is required")
        if any(not isinstance(pid, str) or not pid.strip() for pid in self.dissent_patch_ids):
            raise ModelValidationError("dissent_patch_ids must contain non-empty strings")
        if self.why_not_others is None:
            raise ModelValidationError("why_not_others is required")
        if any(not isinstance(item, str) or not item.strip() for item in self.why_not_others):
            raise ModelValidationError("why_not_others must contain non-empty strings")

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
