"""
BaseAgent — abstract base class for all domain agents.

Every agent:
  1. Calls discover_tools() at startup to learn what the MCP server offers.
  2. Uses mcp_call() for every tool invocation — never hits REST APIs directly.
  3. Implements run(task: dict) -> dict with its own domain logic.

The allowed_tool_names class variable filters the global tool list to only the
tools this agent is allowed to use. This prevents accidental cross-domain calls.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from core.config_loader import get_config
from core.logger import log_event, log_error


class BaseAgent(ABC):
    # Subclasses override this to restrict which tools they can call
    allowed_tool_names: list[str] = []

    def __init__(self, name: str, mcp_base_url: str | None = None):
        self.name = name
        cfg = get_config()
        self.mcp_base_url = mcp_base_url or f"http://localhost:{cfg.server.mcp_port}"
        self.available_tools: dict[str, dict] = {}

    async def discover_tools(self) -> None:
        """Fetch the tool list from MCP server and store the subset this agent can use."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.mcp_base_url}/tools")
            resp.raise_for_status()
            all_tools = resp.json()

        if self.allowed_tool_names:
            self.available_tools = {
                t["name"]: t for t in all_tools if t["name"] in self.allowed_tool_names
            }
        else:
            self.available_tools = {t["name"]: t for t in all_tools}

        log_event(self.name, "tools discovered", list(self.available_tools.keys()))

    async def mcp_call(self, tool_name: str, parameters: dict[str, Any] | None = None) -> Any:
        """
        Invoke a tool via MCP server. Logs the request and response.
        Returns the result payload or raises on failure.
        """
        params = parameters or {}
        log_event("mcp", f"→ {tool_name}", params if params else None)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.mcp_base_url}/tools/invoke",
                json={"tool_name": tool_name, "parameters": params},
            )
            resp.raise_for_status()
            data = resp.json()

        if not data.get("success"):
            error = data.get("error", "unknown error")
            log_error("mcp", f"Tool '{tool_name}' failed: {error}")
            raise RuntimeError(f"MCP tool '{tool_name}' failed: {error}")

        result = data.get("result")
        duration = data.get("duration_ms", 0)
        log_event("mcp", f"← {tool_name} ({duration:.0f}ms)", result)
        return result

    @abstractmethod
    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent's domain logic. Returns a structured JSON result."""
        ...
