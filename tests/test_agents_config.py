from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents import AgentConfigError, build_agent_from_config, persona_mix


def test_build_agent_from_config_requires_human_base():
    raw = {
        "agent_id": "a1",
        "module_weights": {"economics": 1.0},
    }

    try:
        build_agent_from_config(raw)
    except AgentConfigError:
        pass
    else:
        raise AssertionError("expected AgentConfigError when human_base is missing")


def test_build_agent_from_config_and_persona_mix_from_config_file():
    payload = json.loads(Path("config/agents.yaml").read_text(encoding="utf-8"))
    raw = payload["agents"][0]

    agent = build_agent_from_config(raw)
    mix = persona_mix(agent)

    assert agent.agent_id == "agent_a"
    assert "human_base" in mix
    assert mix["human_base"] > 0



def test_build_agent_from_config_fails_on_unknown_module():
    raw = {
        "agent_id": "a2",
        "human_base": {"weight": 0.7, "heuristics": ["h1"]},
        "module_weights": {"unknown_module": 1.0},
    }

    try:
        build_agent_from_config(raw)
    except AgentConfigError as exc:
        assert "unknown perspective module" in str(exc)
    else:
        raise AssertionError("expected AgentConfigError for unknown module")


def test_build_agent_from_config_instantiates_multiple_modules():
    raw = {
        "agent_id": "a3",
        "human_base": {"weight": 0.6, "heuristics": ["h1"]},
        "module_weights": {"economics": 2.0, "psychology": 1.0},
    }

    agent = build_agent_from_config(raw)

    names = {module.name for module in agent.perspective_modules}
    assert names == {"economics", "psychology"}
