from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.artifacts import ArtifactCard, DebateTurn
from src.protocol import ModelValidationError


def test_artifact_status_rejects_invalid_value():
    with pytest.raises(ModelValidationError):
        ArtifactCard(
            artifact_id="idea_1",
            title="title",
            content="content",
            status="unknown_status",
        )


def test_debate_turn_arena_rejects_invalid_value():
    with pytest.raises(ModelValidationError):
        DebateTurn(
            turn_id="turn_1",
            arena="invalid_arena",
            decision="accept",
            message="msg",
        )
