"""
Async Ollama HTTP client wrapping /api/generate and /api/chat.
All LLM calls in this project go through here — one place to change models or base URL.
"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from core.config_loader import get_config


async def generate(
    prompt: str,
    system_prompt: str = "",
    temperature: float | None = None,
    model: str | None = None,
) -> str:
    """Call Ollama /api/generate and return the response text."""
    cfg = get_config()
    payload = {
        "model": model or cfg.models.primary,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature if temperature is not None else cfg.models.temperature},
    }
    if system_prompt:
        payload["system"] = system_prompt

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{cfg.models.ollama_base_url}/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json()["response"].strip()


async def generate_json(
    prompt: str,
    system_prompt: str = "",
    temperature: float | None = None,
    model: str | None = None,
) -> dict[str, Any] | list[Any]:
    """
    Call Ollama expecting a JSON response.
    Extracts the first valid JSON object/array from the response,
    handling cases where the LLM wraps output in markdown fences.
    """
    raw = await generate(prompt, system_prompt=system_prompt, temperature=temperature, model=model)
    return extract_json_from_text(raw)


def extract_json_from_text(text: str, raw_on_failure: bool = False) -> Any:
    """
    Extract and parse the first JSON object or array from an LLM response string.

    Strips markdown code fences, then finds and parses the first { or [ block.

    Args:
        raw_on_failure: If True, return the cleaned text when no JSON is found
            (use when the response may legitimately be plain text, e.g. affirmations).
            If False (default), return {"error": ..., "raw": text} on failure.
    """
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    # If raw_on_failure, only attempt parse when the response looks like JSON
    if raw_on_failure and not cleaned.startswith(("{", "[")):
        return cleaned

    for start_char, end_char in [('{', '}'), ('[', ']')]:
        idx = cleaned.find(start_char)
        if idx == -1:
            continue
        depth = 0
        for i, ch in enumerate(cleaned[idx:], start=idx):
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    candidate = cleaned[idx: i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        if raw_on_failure:
            return cleaned
        return {"error": "Failed to parse JSON from LLM response", "raw": text}
