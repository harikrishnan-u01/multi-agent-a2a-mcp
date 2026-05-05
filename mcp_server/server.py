"""
MCP Server — the unified tool execution gateway (Layer 2).

Three routes:
  GET  /health       → readiness check
  GET  /tools        → list all registered tools (agents call this at startup)
  POST /tools/invoke → execute a tool by name with parameters

At startup: loads all tool definitions from settings.yaml into the registry.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from core.config_loader import get_config
from mcp_server.registry import registry
from mcp_server.tool_types import ToolDefinition, ToolInvokeRequest, ToolInvokeResponse, ToolListItem


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register all tools from config at startup
    cfg = get_config()
    registry.register_from_config(cfg.tools)
    yield
    # Cleanup (nothing to do here)


app = FastAPI(title="MCP Server", version="1.0", lifespan=lifespan)


@app.get("/health")
def health():
    tools = registry.list_tools()
    return {"status": "ok", "service": "mcp_server", "tools_registered": len(tools)}


@app.get("/tools", response_model=list[ToolListItem])
def list_tools():
    """Return all registered tools — agents call this to discover what's available."""
    return registry.list_tools()


@app.post("/tools/register", status_code=201)
def register_tool(tool: ToolDefinition):
    """Dynamically register a new tool at runtime (for extensibility)."""
    try:
        registry.register(tool)
        return {"registered": tool.name}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/tools/invoke", response_model=ToolInvokeResponse)
def invoke_tool(request: ToolInvokeRequest):
    """
    Execute a tool by name. The registry decides whether this becomes
    an HTTP call, a local Python call, or an Ollama LLM call.
    """
    response = registry.invoke(request)
    return response
