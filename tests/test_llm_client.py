import json
from pathlib import Path

import pytest

from src.llm_client import OpenRouterClient
from src.orchestrator import REQUIRED_SAMPLING_KEYS, SEAT_SAMPLING_CONFIG, get_sampling_config_for_seat


@pytest.mark.parametrize("seat", ["proposer", "critic_a", "critic_b", "repairer", "transfer_seat"])
def test_seat_sampling_config_has_required_keys(seat: str):
    cfg = get_sampling_config_for_seat(seat)
    for key in REQUIRED_SAMPLING_KEYS:
        assert key in cfg


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
        return {"id": "resp-1", "choices": [{"message": {"content": "ok"}}]}

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

    trace_file = tmp_path / "round_03_critic_b_trace.json"
    assert trace_file.exists()
    trace = json.loads(trace_file.read_text(encoding="utf-8"))
    assert trace["seat"] == "critic_b"
    assert trace["sampling"]["presence_penalty"] == SEAT_SAMPLING_CONFIG["critic_b"]["presence_penalty"]


def test_unknown_seat_raises_error():
    with pytest.raises(ValueError):
        get_sampling_config_for_seat("critic")
