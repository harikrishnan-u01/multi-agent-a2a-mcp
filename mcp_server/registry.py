"""
ToolRegistry — the core of the MCP design.

This is NOT just a REST proxy. It is a unified tool execution layer that routes
each tool call to the right executor based on the tool's category:
  - "rest"   → httpx call to a mock API
  - "local"  → Python function called directly in-process
  - "ollama" → prompt sent to local Ollama LLM

Agents only know tool names and parameters — the registry decides how to run them.
Adding a new tool requires only a new entry in settings.yaml, no code changes.
"""
from __future__ import annotations

import time
from typing import Any

from mcp_server.tool_types import ToolDefinition, ToolInvokeRequest, ToolInvokeResponse, ToolListItem


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Add a single tool to the registry; raises if the name is already taken."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def register_from_config(self, tools_config: list[dict[str, Any]]) -> None:
        """Bulk-register tools from the settings.yaml tools list at server startup."""
        for tool_dict in tools_config:
            self.register(ToolDefinition(**tool_dict))

    def list_tools(self) -> list[ToolListItem]:
        return [
            ToolListItem(
                name=t.name,
                category=t.category,
                description=t.description,
                parameters=t.parameters,
            )
            for t in self._tools.values()
        ]

    def invoke(self, request: ToolInvokeRequest) -> ToolInvokeResponse:
        tool = self._tools.get(request.tool_name)
        if not tool:
            return ToolInvokeResponse(
                tool_name=request.tool_name,
                success=False,
                error=f"Unknown tool: '{request.tool_name}'. Available: {list(self._tools.keys())}",
            )

        start = time.monotonic()
        try:
            result = self._dispatch(tool, request.parameters)
            return ToolInvokeResponse(
                tool_name=request.tool_name,
                success=True,
                result=result,
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
        except Exception as exc:
            return ToolInvokeResponse(
                tool_name=request.tool_name,
                success=False,
                error=str(exc),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )

    def _dispatch(self, tool: ToolDefinition, parameters: dict[str, Any]) -> Any:
        """Route to the correct executor. Callers never need to know the category."""
        from mcp_server.tools import local_tools, ollama_tools, rest_tools

        match tool.category:
            case "rest":
                return rest_tools.execute(tool, parameters)
            case "local":
                return local_tools.execute(tool, parameters)
            case "ollama":
                return ollama_tools.execute(tool, parameters)
            case _:
                raise ValueError(f"Unknown tool category: '{tool.category}'")


# Module-level singleton — imported by server.py
registry = ToolRegistry()
