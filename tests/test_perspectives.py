from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.perspectives import (
    PerspectiveValidationError,
    get_registered_module_class,
    validate_perspective_output,
)


def test_validate_perspective_output_missing_required_field():
    payload = {
        "observations": [],
        "criticisms": [],
        "revisions": [],
        "risks": [],
        "questions": [],
        "evidence_needs": [],
    }

    try:
        validate_perspective_output(payload)
    except PerspectiveValidationError as exc:
        assert "Missing required audit fields" in str(exc)
    else:
        raise AssertionError("expected PerspectiveValidationError for missing confidence")


def test_validate_perspective_output_rejects_non_numeric_confidence():
    payload = {
        "observations": [],
        "criticisms": [],
        "revisions": [],
        "risks": [],
        "questions": [],
        "evidence_needs": [],
        "confidence": "high",
    }

    try:
        validate_perspective_output(payload)
    except PerspectiveValidationError as exc:
        assert "confidence must be numeric" in str(exc)
    else:
        raise AssertionError("expected PerspectiveValidationError for non-numeric confidence")


def test_module_registry_returns_mvp_modules():
    for name in ("economics", "philosophy", "psychology"):
        module_cls = get_registered_module_class(name)
        assert module_cls is not None
        payload = module_cls().audit({}, {}, [])
        assert "confidence" in payload
