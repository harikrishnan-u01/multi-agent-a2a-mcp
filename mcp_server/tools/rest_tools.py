"""
REST tool executor — makes HTTP calls to Layer 1 mock APIs.

Why go through MCP instead of calling APIs directly from agents?
  1. Agents don't need to know URLs, auth headers, or retry logic.
  2. All tool call logs (timing, payloads) are captured in one place.
  3. You can swap a REST API for a local function without changing agent code.
"""
from __future__ import annotations

from typing import Any

import httpx

from mcp_server.tool_types import ToolDefinition


def execute(tool_def: ToolDefinition, parameters: dict[str, Any]) -> Any:
    """
    Make a synchronous HTTP GET to tool_def.endpoint with parameters as query params.
    Returns parsed JSON. Raises on HTTP errors or timeouts.
    """
    if not tool_def.endpoint:
        raise ValueError(f"Tool '{tool_def.name}' has no endpoint defined")

    # Use GET with query params — all our mock APIs use this pattern
    response = httpx.get(
        tool_def.endpoint,
        params={k: v for k, v in parameters.items() if v is not None},
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()
