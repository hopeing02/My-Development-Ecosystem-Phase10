from __future__ import annotations

import os
from typing import Any


def normalize_usage(usage: dict[str, Any]) -> dict[str, Any]:
    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", usage.get("promptTokenCount", 0)))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", usage.get("candidatesTokenCount", 0)))
    total_tokens = usage.get("total_tokens", usage.get("totalTokenCount"))
    try:
        input_value = int(input_tokens or 0)
        output_value = int(output_tokens or 0)
    except (TypeError, ValueError):
        input_value = 0
        output_value = 0
    try:
        total_value = int(total_tokens) if total_tokens is not None else input_value + output_value
    except (TypeError, ValueError):
        total_value = input_value + output_value
    return {"input_tokens": input_value, "output_tokens": output_value, "total_tokens": total_value, "raw": usage}


def estimate_cost_usd(provider: str, model: str, usage: dict[str, Any]) -> float | None:
    prefix = f"MDE_AI_PRICE_{provider}_{model}".upper().replace("-", "_").replace(".", "_")
    raw_input = os.environ.get(f"{prefix}_INPUT_PER_1M")
    raw_output = os.environ.get(f"{prefix}_OUTPUT_PER_1M")
    if raw_input is None or raw_output is None:
        return None
    normalized = normalize_usage(usage)
    try:
        return round(
            normalized["input_tokens"] * float(raw_input) / 1_000_000
            + normalized["output_tokens"] * float(raw_output) / 1_000_000,
            8,
        )
    except ValueError:
        return None
