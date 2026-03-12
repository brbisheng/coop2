"""OpenRouter client with per-seat sampling injection and trace persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request

from .orchestrator import get_sampling_config_for_seat


@dataclass(slots=True)
class OpenRouterClient:
    """Thin OpenRouter wrapper that applies seat-specific sampling settings."""

    api_key: str
    model: str
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"

    def run_seat(
        self,
        *,
        seat: str,
        round_index: int,
        messages: list[dict[str, Any]],
        trace_dir: str | Path = "traces",
        timeout_s: float = 60.0,
        extra_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sampling = get_sampling_config_for_seat(seat)
        request_body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            **sampling,
        }
        if isinstance(extra_body, dict):
            request_body.update(extra_body)

        payload = self._post_json(
            url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            body=request_body,
            timeout_s=timeout_s,
        )

        self._write_trace(
            trace_dir=Path(trace_dir),
            round_index=round_index,
            seat=seat,
            sampling=sampling,
            request_body=request_body,
            response_body=payload,
        )
        return payload

    def _post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout_s: float,
    ) -> dict[str, Any]:
        req = request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    def _write_trace(
        self,
        *,
        trace_dir: Path,
        round_index: int,
        seat: str,
        sampling: dict[str, Any],
        request_body: dict[str, Any],
        response_body: dict[str, Any],
    ) -> Path:
        trace_dir.mkdir(parents=True, exist_ok=True)
        seat_key = str(seat).strip().lower()
        trace_path = trace_dir / f"round_{int(round_index):02d}_{seat_key}_trace.json"

        trace_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seat": seat_key,
            "round_index": int(round_index),
            "sampling": sampling,
            "request": request_body,
            "response": response_body,
        }
        trace_path.write_text(json.dumps(trace_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return trace_path
