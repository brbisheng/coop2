from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import allocate_seat, run_micro_deliberation, run_perspective_audit_batch


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def test_run_micro_round_produces_commit_event_and_snapshot(tmp_path: Path):
    session = tmp_path / "session_001"

    critiques = [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
        {
            "attack_labels": ["measurement-risk"],
            "challenged_fields": ["outcome_vars"],
            "reasoning_path_labels": ["construct-validity"],
        },
    ]
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v3",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "clarified"}}],
        unresolved_dissents=[
            {
                "dissent_id": "d-1",
                "artifact_id": "artifact_main_v2",
                "status": "open",
                "conflict_type": "mechanism",
                "message": "identification assumption unresolved",
                "why_not": "branch-B removed key mechanism variable",
            }
        ],
        unresolved_dissent_saved=True,
    )

    assert result["commit"]["allowed"] is True
    assert result["commit"]["decision"] == "accept"

    commits = _read_jsonl(session / "commits.jsonl")
    events = _read_jsonl(session / "event_log.jsonl")
    snapshot = json.loads((session / "snapshot.json").read_text(encoding="utf-8"))

    assert len(commits) == 1
    assert len(events) == 6
    assert commits[0]["commit_id"] in snapshot["latest_commits"]
    assert snapshot["artifact_heads"]["artifact_main_v3"]["version"] == "v1"
    assert (session / "artifacts" / "artifact_main_v3" / "v1.json").exists()
    assert commits[0]["proposed_changes"] == [{"mechanism": "clarified"}]
    assert commits[0]["reasons"]
    assert commits[0]["why_not_others"]
    assert commits[0]["dissent_patch_ids"]
    assert commits[0]["conflict_types"] == ["mechanism"]
    assert events[-1]["reasons"]
    assert events[-1]["why_not_others"]
    assert events[-1]["dissent_patch_ids"]
    assert events[-1]["conflict_types"] == ["mechanism"]
    artifact_v1 = json.loads((session / "artifacts" / "artifact_main_v3" / "v1.json").read_text(encoding="utf-8"))
    assert artifact_v1["version"] == "v1"
    assert artifact_v1["parent_ids"] == []
    assert artifact_v1["open_issues"]
    assert artifact_v1["proposed_changes"]
    assert artifact_v1["why_not_others"]
    assert artifact_v1["dissent_patch_ids"]
    assert {
        event["step"]
        for event in events
        if event.get("type", "").startswith("deliberation.") and event.get("step")
    } == {
        "proposal",
        "critique_a",
        "critique_b",
        "repair",
        "decision",
    }
    assert (session / "dissent" / "d-1.json").exists()
    dissent_saved = json.loads((session / "dissent" / "d-1.json").read_text(encoding="utf-8"))
    assert dissent_saved["conflict_type"] == "mechanism"


def test_allocate_seat_uses_conflict_mix_and_history():
    seat = allocate_seat(
        arena="mechanism",
        conflict_type="execution",
        agent_module_mix={"economics": 0.2, "psychology": 0.1, "philosophy": 0.7},
        seat_frequency_history={"critic": 5, "proposer": 0, "repairer": 0},
    )
    assert seat == "repairer"


def test_run_micro_round_defaults_missing_conflict_type_to_execution(tmp_path: Path):
    session = tmp_path / "session_008"
    critiques = [
        {"attack_labels": ["id-risk"], "challenged_fields": ["assumption_set"], "reasoning_path_labels": ["causal-chain"]},
        {"attack_labels": ["measurement-risk"], "challenged_fields": ["outcome_vars"], "reasoning_path_labels": ["construct-validity"]},
    ]
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v8",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "clarified"}}],
        unresolved_dissents=[{"dissent_id": "d-2", "artifact_id": "artifact_main_v8", "status": "open"}],
        unresolved_dissent_saved=True,
    )

    assert result["commit"]["conflict_types"] == ["execution"]
    assert result["event"]["conflict_types"] == ["execution"]
    dissent_saved = json.loads((session / "dissent" / "d-2.json").read_text(encoding="utf-8"))
    assert dissent_saved["conflict_type"] == "execution"


def test_run_micro_round_rejects_commit_when_invariants_fail(tmp_path: Path):
    session = tmp_path / "session_002"

    critiques = [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
    ]
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
        ]
    }

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v3",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "clarified"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )

    assert result["commit"]["allowed"] is False
    assert result["commit"]["decision"] == "park"
    assert "only park/continue_discussion allowed" in result["commit"]["reason"]


def test_missing_obligations_only_allow_park_or_continue(tmp_path: Path):
    session = tmp_path / "session_005"
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }

    commit_attempt = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v5",
        arena="mechanism",
        proposed_action="commit",
        critiques=[{"attack_labels": ["id-risk"]}],
        round_input={
            "proposal": {"present": True},
            "critique_a": {"present": True},
            "critique_b": {"present": False},
            "repair": {"present": True},
            "decision": {"action": "commit"},
        },
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "clarified"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )
    assert commit_attempt["commit"]["allowed"] is False
    assert "required obligations not satisfied" in commit_attempt["commit"]["reason"]
    assert "independent_critiques" in commit_attempt["commit"]["reason"]

    park_attempt = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v5",
        arena="mechanism",
        proposed_action="park",
        critiques=[{"attack_labels": ["id-risk"]}],
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "clarified"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )
    assert park_attempt["commit"]["allowed"] is True
    assert park_attempt["commit"]["decision"] == "park"


def test_structured_round_complete_path_and_standardized_event_types(tmp_path: Path):
    session = tmp_path / "session_006"
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }
    round_input = {
        "proposal": {"claim": "A"},
        "critique_a": {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
        "critique_b": {
            "attack_labels": ["measurement-risk"],
            "challenged_fields": ["outcome_vars"],
            "reasoning_path_labels": ["construct-validity"],
        },
        "repair": {"present": True, "proposed_changes": {"mechanism": "clarified"}},
        "decision": {"action": "commit"},
    }

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_structured",
        arena="mechanism",
        proposed_action="commit",
        critiques=[round_input["critique_a"], round_input["critique_b"]],
        round_input=round_input,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "clarified"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )

    assert result["commit"]["allowed"] is True
    events = _read_jsonl(session / "event_log.jsonl")
    types = {item["type"] for item in events}
    assert {
        "deliberation.round",
        "deliberation.proposal",
        "deliberation.critique_a",
        "deliberation.critique_b",
        "deliberation.repair",
        "deliberation.decision",
    }.issubset(types)


def test_structured_round_missing_step_fails_with_readable_reason(tmp_path: Path):
    session = tmp_path / "session_007"
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_structured",
        arena="mechanism",
        proposed_action="commit",
        critiques=[{"attack_labels": ["id-risk"]}, {"attack_labels": ["measurement-risk"]}],
        round_input={
            "proposal": {"claim": "A"},
            "critique_a": {"attack_labels": ["id-risk"]},
            "critique_b": {"attack_labels": ["measurement-risk"]},
            "repair": None,
            "decision": {"action": "commit"},
        },
        panel_state=panel_state,
        accepted_patches=[],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )

    assert result["commit"]["allowed"] is False
    assert result["commit"]["decision"] == "park"
    assert "structured round input incomplete" in result["commit"]["reason"]
    assert "repair" in result["commit"]["reason"]


def test_lineage_chain_can_be_reconstructed_from_parent_ids(tmp_path: Path):
    session = tmp_path / "session_003"
    critiques = [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
        {
            "attack_labels": ["measurement-risk"],
            "challenged_fields": ["outcome_vars"],
            "reasoning_path_labels": ["construct-validity"],
        },
    ]
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.4, "module_weights": {"economics": 0.6}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
        ]
    }

    first = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v3",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "v1"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )
    second = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v3",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "v2"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
    )

    assert second["commit"]["parent_ids"] == [first["commit"]["commit_id"]]
    assert second["commit"]["version"] == "v2"



def test_run_perspective_audit_batch_with_multiple_modules_is_structured(tmp_path: Path):
    from src.perspectives import EconomicsModule, PsychologyModule

    audits = run_perspective_audit_batch(
        modules=[EconomicsModule(), PsychologyModule()],
        artifact={"artifact_id": "a1"},
        local_context={"arena": "mechanism"},
        unresolved_conflicts=[],
    )

    assert len(audits) == 2
    assert {item["module"] for item in audits} == {"economics", "psychology"}
    for item in audits:
        assert "audit" in item
        assert isinstance(item["audit"]["confidence"], (int, float))

    session = tmp_path / "session_004"
    critiques = [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
        {
            "attack_labels": ["measurement-risk"],
            "challenged_fields": ["outcome_vars"],
            "reasoning_path_labels": ["construct-validity"],
        },
    ]
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.4, "module_weights": {"economics": 0.6}},
            {"agent_id": "a2", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v4",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "audit-informed"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
        perspective_audits=audits,
    )

    assert result["event"]["perspective_audits"]
    assert result["event"]["audit_summary"]["module_count"] == 2
    assert "modules=economics,psychology" in result["event"]["patch_rationale"]


def test_run_perspective_audit_batch_rejects_invalid_module_payload():
    from src.perspectives import PerspectiveValidationError

    class _BrokenModule:
        name = "broken"
        version = "0.1"

        def audit(self, artifact, local_context, unresolved_conflicts):
            return {
                "observations": [],
                "criticisms": [],
                "revisions": [],
                "risks": [],
                "questions": [],
                "evidence_needs": [],
                "evidence_refs": [],
                "evidence_type": "none",
                "evidence_gap": "gap",
            }

    try:
        run_perspective_audit_batch(
            modules=[_BrokenModule()],
            artifact={"artifact_id": "a1"},
            local_context={"arena": "mechanism"},
            unresolved_conflicts=[],
        )
    except PerspectiveValidationError as exc:
        assert "Missing required audit fields" in str(exc)
    else:
        raise AssertionError("expected PerspectiveValidationError for invalid module output")




def test_run_perspective_audit_batch_rejects_fake_evidence_payload():
    from src.perspectives import PerspectiveValidationError

    class _FakeEvidenceModule:
        name = "fake_evidence"
        version = "0.1"

        def audit(self, artifact, local_context, unresolved_conflicts):
            return {
                "observations": ["obs"],
                "criticisms": ["crit"],
                "revisions": ["rev"],
                "risks": ["risk"],
                "questions": ["q"],
                "evidence_needs": ["need"],
                "evidence_refs": ["fake://fabricated"],
                "evidence_type": "empirical",
                "evidence_gap": "",
                "confidence": 0.6,
            }

    try:
        run_perspective_audit_batch(
            modules=[_FakeEvidenceModule()],
            artifact={"artifact_id": "a1"},
            local_context={"arena": "mechanism"},
            unresolved_conflicts=[],
        )
    except PerspectiveValidationError as exc:
        assert "fake evidence" in str(exc)
    else:
        raise AssertionError("expected PerspectiveValidationError for fake evidence")


def test_run_micro_round_surfaces_evidence_gap_in_open_issues_and_reasons(tmp_path: Path):
    session = tmp_path / "session_evidence_gap"
    critiques = [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
        {
            "attack_labels": ["measurement-risk"],
            "challenged_fields": ["outcome_vars"],
            "reasoning_path_labels": ["construct-validity"],
        },
    ]
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.4, "module_weights": {"economics": 0.6}},
            {"agent_id": "a2", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }
    audits = [
        {
            "module": "economics",
            "module_version": "0.1",
            "audit": {
                "observations": ["obs"],
                "criticisms": ["crit"],
                "revisions": ["rev"],
                "risks": ["risk"],
                "questions": ["q"],
                "evidence_needs": ["need"],
                "evidence_refs": [],
                "evidence_type": "none",
                "evidence_gap": "missing baseline dataset",
                "confidence": 0.5,
            },
        }
    ]

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_gap",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "with-gap"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
        perspective_audits=audits,
    )

    assert "evidence_gap: missing baseline dataset" in result["event"]["open_issues"]
    assert "evidence gaps remain unresolved" in result["event"]["reasons"]


def test_run_micro_round_aggregates_three_perspective_modules(tmp_path: Path):
    from src.perspectives import EconomicsModule, PhilosophyModule, PsychologyModule

    audits = run_perspective_audit_batch(
        modules=[EconomicsModule(), PhilosophyModule(), PsychologyModule()],
        artifact={"artifact_id": "a1"},
        local_context={"arena": "mechanism"},
        unresolved_conflicts=[],
    )

    session = tmp_path / "session_006"
    critiques = [
        {
            "attack_labels": ["id-risk"],
            "challenged_fields": ["assumption_set"],
            "reasoning_path_labels": ["causal-chain"],
        },
        {
            "attack_labels": ["measurement-risk"],
            "challenged_fields": ["outcome_vars"],
            "reasoning_path_labels": ["construct-validity"],
        },
    ]
    panel_state = {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.4, "module_weights": {"economics": 0.6}},
            {"agent_id": "a2", "human_base_weight": 0.3, "module_weights": {"philosophy": 0.7}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }

    result = run_micro_deliberation(
        session_dir=session,
        artifact_id="artifact_main_v6",
        arena="mechanism",
        proposed_action="commit",
        critiques=critiques,
        panel_state=panel_state,
        accepted_patches=[{"proposed_changes": {"mechanism": "triple-audit-informed"}}],
        unresolved_dissents=[],
        unresolved_dissent_saved=False,
        perspective_audits=audits,
    )

    summary = result["event"]["audit_summary"]
    assert summary["module_count"] == 3
    assert set(summary["modules"]) == {"economics", "philosophy", "psychology"}
    assert len(summary["revisions"]) == 3
    assert "modules=economics,philosophy,psychology" in result["event"]["patch_rationale"]
