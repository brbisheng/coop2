import json
from pathlib import Path

import pytest

from src.llm_client import OpenRouterClient
from src.orchestrator import (
    REQUIRED_SAMPLING_KEYS,
    SEAT_PROMPT_TEMPLATE,
    SEAT_SAMPLING_CONFIG,
    build_seat_context,
    get_prompt_template_for_seat,
    get_sampling_config_for_seat,
    validate_transfer_payload,
    validate_seat_output,
)


@pytest.mark.parametrize("seat", ["proposer", "critic_a", "critic_b", "repairer", "transfer_seat"])
def test_seat_sampling_config_has_required_keys(seat: str):
    cfg = get_sampling_config_for_seat(seat)
    for key in REQUIRED_SAMPLING_KEYS:
        assert key in cfg


@pytest.mark.parametrize("seat", ["proposer", "critic_a", "critic_b", "repairer", "transfer_seat"])
def test_seat_prompt_template_has_objective_and_failure_condition(seat: str):
    template = get_prompt_template_for_seat(seat)
    assert template["objective"]
    assert template["failure_condition"]


def test_get_sampling_config_for_seat_returns_copy():
    cfg = get_sampling_config_for_seat("proposer")
    cfg["temperature"] = -1
    assert SEAT_SAMPLING_CONFIG["proposer"]["temperature"] != -1


def test_openrouter_client_injects_per_seat_sampling_and_persists_trace(monkeypatch, tmp_path: Path):
    captured: dict[str, object] = {}

    def fake_post_json(self, *, url, headers, body, timeout_s):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = body
        captured["timeout"] = timeout_s
        return {"id": "resp-1", "choices": [{"message": {"content": "{\"attack_labels\": [\"measurement-risk\"], \"challenged_fields\": [\"outcome\"], \"reasoning_path_labels\": [\"alternative-path\"], \"flip_condition\": \"independent falsifier\", \"evidence_refs\": [\"paper-x\"]}"}}]}

    monkeypatch.setattr(OpenRouterClient, "_post_json", fake_post_json)

    client = OpenRouterClient(api_key="k", model="openai/gpt-4o-mini")
    payload = client.run_seat(
        seat="critic_b",
        round_index=3,
        messages=[{"role": "user", "content": "hello"}],
        trace_dir=tmp_path,
    )

    assert payload["id"] == "resp-1"
    body = captured["json"]
    assert isinstance(body, dict)
    assert body["temperature"] == SEAT_SAMPLING_CONFIG["critic_b"]["temperature"]
    assert body["presence_penalty"] == SEAT_SAMPLING_CONFIG["critic_b"]["presence_penalty"]
    assert body["messages"][0]["role"] == "system"
    assert SEAT_PROMPT_TEMPLATE["critic_b"]["objective"] in body["messages"][0]["content"]

    trace_file = tmp_path / "round_03_critic_b_trace.json"
    assert trace_file.exists()
    trace = json.loads(trace_file.read_text(encoding="utf-8"))
    assert trace["seat"] == "critic_b"
    assert trace["sampling"]["presence_penalty"] == SEAT_SAMPLING_CONFIG["critic_b"]["presence_penalty"]
    assert trace["local_validation"]["is_valid"] is True


def test_openrouter_client_retries_once_when_local_validation_fails(monkeypatch, tmp_path: Path):
    calls: list[dict[str, object]] = []

    def fake_post_json(self, *, url, headers, body, timeout_s):
        calls.append(body)
        if len(calls) == 1:
            return {"id": "resp-initial", "choices": [{"message": {"content": "just rhetoric"}}]}
        return {
            "id": "resp-retry",
            "choices": [{"message": {"content": "结构迁移 with constraint and causal mapping"}}],
        }

    monkeypatch.setattr(OpenRouterClient, "_post_json", fake_post_json)

    client = OpenRouterClient(api_key="k", model="openai/gpt-4o-mini")
    payload = client.run_seat(
        seat="transfer_seat",
        round_index=8,
        messages=[{"role": "user", "content": "hello"}],
        trace_dir=tmp_path,
    )

    assert payload["id"] == "resp-retry"
    assert len(calls) == 2
    retry_messages = calls[1]["messages"]
    assert "你重复了/违反了以下约束" in retry_messages[-1]["content"]

    trace_file = tmp_path / "round_08_transfer_seat_trace.json"
    trace = json.loads(trace_file.read_text(encoding="utf-8"))
    assert trace["retry"]["attempted"] is True
    assert trace["retry"]["failure_reasons"]


def test_unknown_seat_raises_error():
    with pytest.raises(ValueError):
        get_sampling_config_for_seat("critic")


def test_build_seat_context_windows():
    round_state = {
        "topic": "t",
        "history_summary": "h",
        "proposal": {"p": 1},
        "minimal_evidence": ["e1"],
        "critique_a": {"a": 1},
        "critique_b": {"b": 1},
        "transfer": {"x": 1},
    }

    assert build_seat_context(round_state, "proposer") == {"topic": "t", "history_summary": "h"}
    assert build_seat_context(round_state, "critic_a") == {
        "proposal": {"p": 1},
        "minimal_evidence": ["e1"],
        "critique_b": {"b": 1},
    }
    assert build_seat_context(round_state, "critic_b") == {"proposal": {"p": 1}, "critique_a": {"a": 1}}
    assert build_seat_context(round_state, "repairer") == {
        "proposal": {"p": 1},
        "critique_a": {"a": 1},
        "critique_b": {"b": 1},
        "transfer": {"x": 1},
    }
    assert build_seat_context(round_state, "transfer_seat") == {"proposal": {"p": 1}, "critique": {"a": 1}}


def test_openrouter_client_persists_seat_context_trace(monkeypatch, tmp_path: Path):
    def fake_post_json(self, *, url, headers, body, timeout_s):
        return {"id": "resp-2", "choices": [{"message": {"content": "{\"addressed_attacks\": [{\"attack_labels\": [\"id-risk\"], \"challenged_fields\": [\"assumption_set\"], \"reasoning_path_labels\": [\"causal-chain\"], \"flip_condition\": \"if IV fails\", \"evidence_refs\": [\"doi:1\"]}], \"not_addressed_attacks\": [], \"patch\": {\"mechanism\": \"tighten\"}, \"new_testable_implication\": \"predicts stronger effect under x\"}"}}]}

    monkeypatch.setattr(OpenRouterClient, "_post_json", fake_post_json)

    client = OpenRouterClient(api_key="k", model="openai/gpt-4o-mini")
    client.run_seat(
        seat="repairer",
        round_index=4,
        messages=[{"role": "user", "content": "hello"}],
        trace_dir=tmp_path,
        round_state={
            "proposal": {"id": "p1"},
            "critique_a": {"id": "c1"},
            "critique_b": {"id": "c2"},
            "transfer": {"id": "t1"},
        },
    )

    context_file = tmp_path / "round_04_repairer_context.json"
    assert context_file.exists()
    payload = json.loads(context_file.read_text(encoding="utf-8"))
    assert payload["seat"] == "repairer"
    assert sorted(payload["seat_context"].keys()) == ["critique_a", "critique_b", "proposal", "transfer"]


def test_validate_seat_output_enforces_unified_critic_and_repair_fields():
    critic_ok, critic_reasons = validate_seat_output(
        seat="critic_a",
        output_text='{"attack_labels": ["a"], "challenged_fields": ["f"], "reasoning_path_labels": ["r"], "flip_condition": "c", "evidence_refs": ["e"], "summary": "fragile"}',
        seat_context={},
    )
    assert critic_ok is True
    assert critic_reasons == []

    repair_ok, repair_reasons = validate_seat_output(
        seat="repairer",
        output_text='{"addressed_attacks": [], "not_addressed_attacks": [], "patch": {}, "new_testable_implication": "x", "summary": "minimal cover risk"}',
        seat_context={},
    )
    assert repair_ok is True
    assert repair_reasons == []

    critic_bad, critic_bad_reasons = validate_seat_output(
        seat="critic_b",
        output_text='{"attack_labels": ["a"]}',
        seat_context={},
    )
    assert critic_bad is False
    assert any("缺少字段" in reason for reason in critic_bad_reasons)


def test_validate_transfer_payload_requires_exact_four_slots():
    ok, reasons, parsed = validate_transfer_payload(
        '{"source_domain_mechanism": "m", "structural_mapping": "s", "breakpoints": ["b1"], "new_testable_implications": "n"}'
    )
    assert ok is True
    assert reasons == []
    assert isinstance(parsed, dict)

    bad_ok, bad_reasons, _ = validate_transfer_payload(
        '{"source_domain_mechanism": "m", "structural_mapping": "s", "breakpoints": ["b1"], "extra": 1}'
    )
    assert bad_ok is False
    assert any("缺少字段: new_testable_implications" in reason for reason in bad_reasons)
    assert any("仅允许四格字段" in reason for reason in bad_reasons)


def test_repairer_must_cover_transfer_breakpoints():
    valid, reasons = validate_seat_output(
        seat="repairer",
        output_text='{"addressed_attacks": [], "not_addressed_attacks": [], "patch": {}, "new_testable_implication": "minimal cover risk", "responded_breakpoints": ["bp-a", "bp-b"], "summary": "minimal cover risk"}',
        seat_context={"transfer_breakpoints": ["bp-a", "bp-b"]},
    )
    assert valid is True
    assert reasons == []

    invalid, invalid_reasons = validate_seat_output(
        seat="repairer",
        output_text='{"addressed_attacks": [], "not_addressed_attacks": [], "patch": {}, "new_testable_implication": "minimal cover risk", "responded_breakpoints": ["bp-a"], "summary": "minimal cover risk"}',
        seat_context={"transfer_breakpoints": ["bp-a", "bp-b"]},
    )
    assert invalid is False
    assert any("repair 必须逐条回应 transfer breakpoints" in reason for reason in invalid_reasons)
