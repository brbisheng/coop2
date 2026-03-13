"""Lightweight HTTP service facade wrapping core service API calls."""

from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Any, Iterator

from flask import Flask, jsonify, request

from .service_api import ServiceApiValidationError, build_continuation, read_artifact, run_round

_DEFAULT_API_KEY_ENV = "OPENROUTER_API_KEY"


@contextmanager
def _temporary_openrouter_api_key(api_key: str | None) -> Iterator[None]:
    if not api_key:
        yield
        return

    previous_value = os.environ.get(_DEFAULT_API_KEY_ENV)
    os.environ[_DEFAULT_API_KEY_ENV] = api_key
    try:
        yield
    finally:
        if previous_value is None:
            os.environ.pop(_DEFAULT_API_KEY_ENV, None)
        else:
            os.environ[_DEFAULT_API_KEY_ENV] = previous_value


def _resolve_api_key() -> str | None:
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return token

    x_api_key = request.headers.get("X-API-Key", "").strip()
    if x_api_key:
        return x_api_key

    return os.getenv(_DEFAULT_API_KEY_ENV, "").strip() or None


def _json_body() -> dict[str, Any] | None:
    body = request.get_json(silent=True)
    if body is None:
        return {}
    return body if isinstance(body, dict) else None


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health() -> Any:
        return jsonify({"status": "ok"})

    @app.post("/run-round")
    def run_round_route() -> Any:
        try:
            with _temporary_openrouter_api_key(_resolve_api_key()):
                payload = run_round(_json_body())
            return jsonify(payload)
        except ServiceApiValidationError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/continuation")
    def continuation_route() -> Any:
        try:
            with _temporary_openrouter_api_key(_resolve_api_key()):
                payload = build_continuation(_json_body())
            return jsonify(payload)
        except ServiceApiValidationError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/artifact")
    def artifact_route() -> Any:
        try:
            with _temporary_openrouter_api_key(_resolve_api_key()):
                payload = read_artifact(_json_body())
            return jsonify(payload)
        except ServiceApiValidationError as exc:
            return jsonify({"error": str(exc)}), 400

    return app


app = create_app()
