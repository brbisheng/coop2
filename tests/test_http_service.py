from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.http_service import create_app


def _panel_state() -> dict:
    return {
        "agents": [
            {"agent_id": "a1", "human_base_weight": 0.5, "module_weights": {"economics": 0.5}},
            {"agent_id": "a2", "human_base_weight": 0.2, "module_weights": {"philosophy": 0.8}},
            {"agent_id": "a3", "human_base_weight": 0.3, "module_weights": {"psychology": 0.7}},
        ]
    }


def _critiques() -> list[dict]:
    return [
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


def test_health_route() -> None:
    app = create_app()
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_run_round_continuation_artifact_routes(tmp_path: Path) -> None:
    app = create_app()
    client = app.test_client()
    session_dir = tmp_path / "session_http_1"

    run_payload = {
        "session_dir": str(session_dir),
        "artifact_id": "artifact_main",
        "arena": "mechanism",
        "proposed_action": "commit",
        "critiques": _critiques(),
        "panel_state": _panel_state(),
        "accepted_patches": [{"proposed_changes": {"mechanism": "clarified"}}],
    }

    run_response = client.post("/run-round", json=run_payload)
    assert run_response.status_code == 200
    run_data = run_response.get_json()
    assert run_data["commit"]["artifact_id"] == "artifact_main"

    continuation_response = client.post(
        "/continuation",
        json={
            "session_dir": str(session_dir),
            "goal": "resume",
            "target_artifact_id": "artifact_main",
        },
    )
    assert continuation_response.status_code == 200
    continuation_data = continuation_response.get_json()
    assert continuation_data["target_artifact_id"] == "artifact_main"

    artifact_response = client.post(
        "/artifact",
        json={"session_dir": str(session_dir), "artifact_id": "artifact_main"},
    )
    assert artifact_response.status_code == 200
    artifact_data = artifact_response.get_json()
    assert artifact_data["version"] == "v1"


def test_run_round_uses_api_key_from_headers_and_restores_env(tmp_path: Path) -> None:
    app = create_app()
    client = app.test_client()
    session_dir = tmp_path / "session_http_2"

    os.environ.pop("OPENROUTER_API_KEY", None)
    run_payload = {
        "session_dir": str(session_dir),
        "artifact_id": "artifact_main",
        "arena": "mechanism",
        "proposed_action": "commit",
        "critiques": _critiques(),
        "panel_state": _panel_state(),
    }

    response = client.post(
        "/run-round",
        json=run_payload,
        headers={"X-API-Key": "header-secret"},
    )

    assert response.status_code == 200
    assert "OPENROUTER_API_KEY" not in os.environ


def test_validation_error_maps_to_400(tmp_path: Path) -> None:
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/run-round",
        json={
            "session_dir": str(tmp_path / "session_http_3"),
            "artifact_id": "artifact_main",
            "arena": "mechanism",
            "proposed_action": "commit",
            "critiques": _critiques(),
        },
    )

    assert response.status_code == 400
    assert "panel_state" in response.get_json()["error"]
