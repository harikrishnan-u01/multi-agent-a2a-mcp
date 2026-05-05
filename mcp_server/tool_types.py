"""
Pydantic models for the MCP tool system.
ToolDefinition describes a tool (loaded from config).
ToolInvokeRequest/Response are the wire format for tool calls.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    category: Literal["rest", "local", "ollama"]
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)

    # REST tools: the URL to call
    endpoint: str | None = None

    # Local tools: "module.path.function_name"
    handler: str | None = None

    # Ollama tools: system prompt injected into every call
    system_prompt: str | None = None
    temperature_override: float | None = None


class ToolInvokeRequest(BaseModel):
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolInvokeResponse(BaseModel):
    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class ToolListItem(BaseModel):
    name: str
    category: str
    description: str
    parameters: dict[str, Any]
