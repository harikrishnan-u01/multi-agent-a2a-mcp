"""
Ollama tool executor — calls the local LLM for generative sub-tasks.

Why Ollama via MCP instead of directly from agents?
  All three tool categories (REST, local, Ollama) look identical to agents.
  This lets you replace Ollama with a cloud API without touching any agent code.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from core.config_loader import get_config
from core.ollama_client import extract_json_from_text
from mcp_server.tool_types import ToolDefinition


def execute(tool_def: ToolDefinition, parameters: dict[str, Any]) -> Any:
    """
    Synchronous wrapper — constructs a prompt from parameters + system_prompt,
    calls Ollama /api/generate, and returns the response (parsed as JSON if possible).
    Called from the FastAPI route handler (sync context).
    """
    cfg = get_config()
    system_prompt = tool_def.system_prompt or ""
    temperature = tool_def.temperature_override if tool_def.temperature_override is not None else cfg.models.temperature

    # Build the user prompt from the parameters
    if len(parameters) == 1:
        prompt = str(list(parameters.values())[0])
    else:
        prompt = json.dumps(parameters, indent=2)

    payload = {
        "model": cfg.models.primary,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system_prompt:
        payload["system"] = system_prompt

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(f"{cfg.models.ollama_base_url}/api/generate", json=payload)
        resp.raise_for_status()
        raw = resp.json()["response"].strip()

    # Parse as JSON if the response looks like JSON, otherwise return raw text
    return extract_json_from_text(raw, raw_on_failure=True)
