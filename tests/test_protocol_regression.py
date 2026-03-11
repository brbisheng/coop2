from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.protocol import ArtifactStatus, DebateArena, DebateDecision, parse_enum
from src.storage import ensure_current_schema


def test_legacy_enum_inputs_match_migrated_values():
    legacy_record = {
        "schema_version": 1,
        "status": "archived",
        "decision": "defer",
        "requested_action": "commit",
        "arena": "general",
    }
    migrated = ensure_current_schema(legacy_record)

    parsed_status = parse_enum("archived", ArtifactStatus, "status").value
    parsed_decision = parse_enum("defer", DebateDecision, "decision").value
    parsed_arena = parse_enum("general", DebateArena, "arena").value

    assert parsed_status == migrated["status"]
    assert parsed_decision == migrated["decision"]
    assert parse_enum("commit", DebateDecision, "requested_action").value == migrated["requested_action"]
    assert parsed_arena == migrated["arena"]


def test_new_canonical_values_round_trip():
    assert parse_enum("accept", ArtifactStatus, "status").value == "accept"
    assert parse_enum("branch", DebateDecision, "decision").value == "branch"
    assert parse_enum("mechanism", DebateArena, "arena").value == "mechanism"
