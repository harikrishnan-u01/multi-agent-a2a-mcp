"""
Local tool executors — pure Python, no external HTTP calls.
These tools run inside the MCP server process itself.

Why local tools in MCP?
  Even simple utilities should go through MCP so agents have one consistent
  interface for everything — they don't need to know if a tool hits a URL or
  runs locally.
"""
from __future__ import annotations

import ast
import importlib
import operator
from datetime import date, datetime, timedelta
from typing import Any

from mcp_server.tool_types import ToolDefinition


def get_current_date(**kwargs) -> dict:
    """Returns today's date, day of week, and the upcoming Saturday/Sunday dates."""
    today = date.today()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0:
        saturday = today
    else:
        saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)

    return {
        "today": today.isoformat(),
        "day_of_week": today.strftime("%A"),
        "upcoming_saturday": saturday.isoformat(),
        "upcoming_sunday": sunday.isoformat(),
        "weekend_label": f"{saturday.strftime('%B %d')} – {sunday.strftime('%B %d, %Y')}",
    }


def calculate(expression: str, **kwargs) -> dict:
    """
    Safely evaluate a math expression using AST parsing.
    Never uses eval() — only allows arithmetic operators and numbers.
    """
    _ALLOWED_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _ALLOWED_OPS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            return _ALLOWED_OPS[op_type](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_eval(node.operand)
        else:
            raise ValueError(f"Unsupported expression element: {type(node).__name__}")

    tree = ast.parse(expression, mode="eval")
    result = _eval(tree.body)
    return {"expression": expression, "result": result}


def build_time_blocks(activities: list[dict], duration_hours: float = 8.0, **kwargs) -> dict:
    """
    Distribute a list of activities into morning / afternoon / evening blocks.

    Each activity dict needs at minimum: {name, duration_min}.
    Optional: {time_of_day: "morning"|"afternoon"|"evening"} — respected when provided.
    Remaining activities are distributed evenly across blocks.
    """
    blocks: dict[str, list[dict]] = {"morning": [], "afternoon": [], "evening": []}
    unassigned = []

    for act in activities:
        tod = act.get("time_of_day", "").lower()
        if tod in blocks:
            blocks[tod].append(act)
        else:
            unassigned.append(act)

    # Round-robin distribute unassigned
    slot_cycle = ["morning", "afternoon", "evening"]
    for i, act in enumerate(unassigned):
        blocks[slot_cycle[i % 3]].append(act)

    # Add time hints to each block
    result = {}
    time_ranges = {
        "morning": "7:00 AM – 12:00 PM",
        "afternoon": "12:00 PM – 5:00 PM",
        "evening": "5:00 PM – 9:00 PM",
    }
    for slot, acts in blocks.items():
        result[slot] = {
            "time_range": time_ranges[slot],
            "activities": acts,
            "total_minutes": sum(a.get("duration_min", 0) for a in acts),
        }

    return result


def execute(tool_def: ToolDefinition, parameters: dict[str, Any]) -> Any:
    """
    Dynamically import and call the function named in tool_def.handler.
    The handler string format: "module.path.function_name"
    """
    handler_path = tool_def.handler
    if not handler_path:
        raise ValueError(f"Tool '{tool_def.name}' has no handler defined")

    module_path, func_name = handler_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    return func(**parameters)
