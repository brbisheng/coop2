import json
from pathlib import Path

from src.auto_debate import AutoDebateConfig, run_auto_debate


def test_run_auto_debate_writes_round_traces(monkeypatch, tmp_path: Path):
    session_dir = tmp_path / "session_auto"

    def fake_build_continuation(payload):
        return {
            "goal": payload["goal"],
            "target_artifact_id": payload["target_artifact_id"],
            "arena": "mechanism",
            "minimal_context": {"evidence_refs": ["paper-1"]},
            "unresolved_conflicts": [],
        }

    def fake_read_artifact(payload):
        return {
            "artifact_id": payload["artifact_id"],
            "version": "v1",
            "content": {"claim": "base"},
        }

    seat_payloads = {
        "proposer": {"hypothesis": "h", "mechanism": "m", "prediction": "p"},
        "critic_a": {
            "attack_labels": ["a1"],
            "challenged_fields": ["mechanism"],
            "reasoning_path_labels": ["path-a"],
            "flip_condition": "flip-a",
            "evidence_refs": ["e1"],
            "summary": "s1",
        },
        "critic_b": {
            "attack_labels": ["b1"],
            "challenged_fields": ["prediction"],
            "reasoning_path_labels": ["path-b"],
            "flip_condition": "flip-b",
            "evidence_refs": ["e2"],
            "summary": "s2",
        },
        "transfer_seat": {
            "source_domain_mechanism": "sm",
            "structural_mapping": "map",
            "breakpoints": ["bp"],
            "new_testable_implications": "imp",
        },
        "repairer": {
            "addressed_attacks": [],
            "not_addressed_attacks": [],
            "patch": {"mechanism": "m2"},
            "new_testable_implication": "n",
            "responded_breakpoints": ["bp"],
            "summary": "ok",
        },
    }

    def fake_run_seat(self, *, seat, round_index, messages, trace_dir, timeout_s=60.0, extra_body=None, round_state=None):
        content = json.dumps(seat_payloads[seat], ensure_ascii=False)
        return {"id": f"{seat}-{round_index}", "choices": [{"message": {"content": content}}]}

    run_round_calls: list[dict] = []

    def fake_run_round(payload):
        run_round_calls.append(payload)
        return {
            "commit": {"allowed": True, "decision": "accept", "reason": "ok"},
            "event": {"attack_response_alignment": {"unresolved_dissents": []}},
            "snapshot": {"artifacts": []},
            "round_report": {"commit_decision": {"allowed": True, "decision": "accept", "reason": "ok"}},
            "dry_run": False,
        }

    monkeypatch.setattr("src.auto_debate.build_continuation", fake_build_continuation)
    monkeypatch.setattr("src.auto_debate.read_artifact", fake_read_artifact)
    monkeypatch.setattr("src.auto_debate.OpenRouterClient.run_seat", fake_run_seat)
    monkeypatch.setattr("src.auto_debate.run_round", fake_run_round)

    config = AutoDebateConfig(
        topic="topic-x",
        api_key="k",
        model="m",
        rounds=2,
        session_dir=session_dir,
    )
    results = run_auto_debate(config)

    assert len(results) == 2
    assert len(run_round_calls) == 2
    traces = session_dir / "traces"
    for idx in (1, 2):
        prefix = traces / f"round_{idx:04d}"
        assert Path(str(prefix) + "_request.json").exists()
        assert Path(str(prefix) + "_response.json").exists()
        assert Path(str(prefix) + "_context.json").exists()
        assert Path(str(prefix) + "_alignment.json").exists()
        assert Path(str(prefix) + "_decision.json").exists()
