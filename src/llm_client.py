"""OpenRouter client with per-seat sampling injection and trace persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request

from .orchestrator import (
    build_retry_correction_message,
    build_seat_context,
    build_seat_instruction_message,
    get_sampling_config_for_seat,
    validate_seat_output,
)


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
        round_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sampling = get_sampling_config_for_seat(seat)
        seat_context = build_seat_context(round_state or {}, seat) if isinstance(round_state, dict) else {}

        final_messages = [build_seat_instruction_message(seat, seat_context), *messages]
        request_body: dict[str, Any] = {
            "model": self.model,
            "messages": final_messages,
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

        validation = self._validate_payload_output(seat=seat, payload=payload, seat_context=seat_context)
        retry_trace: dict[str, Any] = {
            "attempted": False,
            "failure_reasons": validation["reasons"],
            "retry_reason": None,
        }
        if not validation["is_valid"]:
            retry_trace["attempted"] = True
            retry_trace["retry_reason"] = f"本地校验失败: {'; '.join(validation['reasons'])}"
            retry_body = dict(request_body)
            retry_body["messages"] = [*final_messages, build_retry_correction_message(validation["reasons"])]
            payload = self._post_json(
                url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                body=retry_body,
                timeout_s=timeout_s,
            )

        self._write_trace(
            trace_dir=Path(trace_dir),
            round_index=round_index,
            seat=seat,
            sampling=sampling,
            request_body=request_body,
            response_body=payload,
            validation=validation,
            retry_trace=retry_trace,
        )
        if seat_context:
            self._write_context(
                trace_dir=Path(trace_dir),
                round_index=round_index,
                seat=seat,
                seat_context=seat_context,
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
        validation: dict[str, Any],
        retry_trace: dict[str, Any],
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
            "local_validation": validation,
            "retry": retry_trace,
        }
        trace_path.write_text(json.dumps(trace_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return trace_path

    def _write_context(
        self,
        *,
        trace_dir: Path,
        round_index: int,
        seat: str,
        seat_context: dict[str, Any],
    ) -> Path:
        trace_dir.mkdir(parents=True, exist_ok=True)
        seat_key = str(seat).strip().lower()
        context_path = trace_dir / f"round_{int(round_index):02d}_{seat_key}_context.json"
        context_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seat": seat_key,
            "round_index": int(round_index),
            "seat_context": seat_context,
        }
        context_path.write_text(json.dumps(context_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return context_path

    def _validate_payload_output(
        self,
        *,
        seat: str,
        payload: dict[str, Any],
        seat_context: dict[str, Any],
    ) -> dict[str, Any]:
        choices = payload.get("choices")
        first_choice = choices[0] if isinstance(choices, list) and choices else {}
        message = first_choice.get("message") if isinstance(first_choice, dict) else {}
        content = message.get("content", "") if isinstance(message, dict) else ""

        is_valid, reasons = validate_seat_output(seat=seat, output_text=content, seat_context=seat_context)
        return {
            "is_valid": is_valid,
            "reasons": reasons,
            "validated_content_length": len(str(content)),
        }
