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
        "evidence_refs": [],
        "evidence_type": "none",
        "evidence_gap": "need baseline evidence",
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
        "evidence_refs": ["doi:10.1000/test"],
        "evidence_type": "empirical",
        "evidence_gap": "",
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


def test_register_perspective_module_supports_dynamic_registration():
    from src.perspectives import BasePerspectiveModule, register_perspective_module

    class _TempModule(BasePerspectiveModule):
        name = "temp_module"
        version = "0.1"

        def audit(self, artifact, local_context, unresolved_conflicts):
            return self._validated(
                {
                    "observations": [],
                    "criticisms": [],
                    "revisions": [],
                    "risks": [],
                    "questions": [],
                    "evidence_needs": [],
                    "evidence_refs": ["doi:10.1000/temp"],
                    "evidence_type": "empirical",
                    "evidence_gap": "",
                    "confidence": 0.1,
                }
            )

    register_perspective_module(_TempModule)
    assert get_registered_module_class("temp_module") is _TempModule


def test_validate_perspective_output_rejects_missing_evidence_completeness():
    payload = {
        "observations": ["obs"],
        "criticisms": ["crit"],
        "revisions": ["rev"],
        "risks": ["risk"],
        "questions": ["q"],
        "evidence_needs": ["need"],
        "evidence_refs": [],
        "evidence_type": "empirical",
        "evidence_gap": "",
        "confidence": 0.8,
    }

    try:
        validate_perspective_output(payload)
    except PerspectiveValidationError as exc:
        assert "minimal evidence completeness failed" in str(exc)
    else:
        raise AssertionError("expected PerspectiveValidationError for missing evidence completeness")


def test_validate_perspective_output_rejects_fake_evidence():
    payload = {
        "observations": ["obs"],
        "criticisms": ["crit"],
        "revisions": ["rev"],
        "risks": ["risk"],
        "questions": ["q"],
        "evidence_needs": ["need"],
        "evidence_refs": ["fake://made-up-source"],
        "evidence_type": "empirical",
        "evidence_gap": "",
        "confidence": 0.8,
    }

    try:
        validate_perspective_output(payload)
    except PerspectiveValidationError as exc:
        assert "fake evidence" in str(exc)
    else:
        raise AssertionError("expected PerspectiveValidationError for fake evidence")
