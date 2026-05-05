"""
MCP smoke test — invokes every registered tool and reports pass/fail.
Run this after starting services to verify the full tool registry works.

Usage:
  # In one terminal: python scripts/start_services.sh (or python main.py in another window)
  python scripts/test_mcp.py
"""
from __future__ import annotations

import json
import sys

import httpx
from rich.console import Console
from rich.table import Table

console = Console()
MCP_BASE = "http://localhost:8000"

TEST_CASES = [
    # (tool_name, parameters, description)
    ("get_current_date",          {},                                  "Local: date calculation"),
    ("calculate",                 {"expression": "42 * 2 + 8"},        "Local: safe math eval"),
    ("build_time_blocks",         {"activities": [{"name": "Yoga", "duration_min": 30}], "duration_hours": 8}, "Local: time blocking"),
    ("get_wellness_activities",   {"type": "relaxation"},              "REST: wellness API relaxation"),
    ("get_wellness_activities",   {"type": "fitness"},                 "REST: wellness API fitness"),
    ("get_meals",                 {"goal": "healthy"},                 "REST: wellness API meals"),
    ("get_sleep_tips",            {},                                  "REST: wellness API sleep tips"),
    ("get_learning_topics",       {"category": "tech"},               "REST: learning API topics"),
    ("get_learning_resources",    {"topic_id": "t1"},                 "REST: learning API resources"),
    ("get_study_schedule",        {"topic": "Python", "available_hours": 2}, "REST: learning API schedule"),
    ("generate_affirmation",      {"theme": "mindfulness"},           "Ollama: affirmation generation"),
    ("parse_intent",              {"user_input": "I want to relax and learn Python"}, "Ollama: intent parsing"),
]


def run_tests():
    # First check health
    try:
        r = httpx.get(f"{MCP_BASE}/health", timeout=5.0)
        health = r.json()
        console.print(f"\n[green]MCP Server healthy[/green] — {health['tools_registered']} tools registered\n")
    except Exception as e:
        console.print(f"[red]MCP Server not reachable: {e}[/red]")
        console.print("Start services first: python main.py  OR  bash scripts/start_services.sh")
        sys.exit(1)

    table = Table(title="MCP Tool Smoke Tests", show_lines=True)
    table.add_column("Tool", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="bold")
    table.add_column("Duration (ms)", style="dim")
    table.add_column("Result Preview", style="dim", max_width=50)

    passed = 0
    failed = 0

    for tool_name, params, description in TEST_CASES:
        try:
            resp = httpx.post(
                f"{MCP_BASE}/tools/invoke",
                json={"tool_name": tool_name, "parameters": params},
                timeout=60.0,
            )
            data = resp.json()
            if data.get("success"):
                result_preview = json.dumps(data.get("result", ""), default=str)[:60]
                table.add_row(tool_name, description, "[green]PASS ✓[/green]",
                              str(data.get("duration_ms", 0)), result_preview)
                passed += 1
            else:
                table.add_row(tool_name, description, "[red]FAIL ✗[/red]",
                              str(data.get("duration_ms", 0)), data.get("error", "")[:60])
                failed += 1
        except Exception as e:
            table.add_row(tool_name, description, "[red]ERROR ✗[/red]", "-", str(e)[:60])
            failed += 1

    console.print(table)
    console.print(f"\n[bold]Results: [green]{passed} passed[/green] / [red]{failed} failed[/red] / {len(TEST_CASES)} total[/bold]\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_tests()
