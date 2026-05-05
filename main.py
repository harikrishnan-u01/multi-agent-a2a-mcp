"""
main.py — single entrypoint for the entire system.

Phase 1: Start all three FastAPI services as subprocesses and wait until healthy.
Phase 2: Run the orchestrator pipeline against a user goal.
Phase 3: Display the final plan in Rich panels and shut down services.

Run: python main.py
  or: python main.py "I want to learn AI and do some yoga this weekend"
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from typing import Any

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from core.logger import log_start, log_event

console = Console()


# ── Service management ────────────────────────────────────────────────────────

SERVICES = [
    # ── Layer 1: Mock REST APIs ───────────────────────────────────────────────
    {
        "name": "wellness_api",
        "cmd": [sys.executable, "-m", "uvicorn", "mock_apis.wellness_api:app", "--port", "8001", "--log-level", "warning"],
        "health_url": "http://localhost:8001/health",
    },
    {
        "name": "learning_api",
        "cmd": [sys.executable, "-m", "uvicorn", "mock_apis.learning_api:app", "--port", "8002", "--log-level", "warning"],
        "health_url": "http://localhost:8002/health",
    },
    # ── Layer 2: MCP Server ───────────────────────────────────────────────────
    {
        "name": "mcp_server",
        "cmd": [sys.executable, "-m", "uvicorn", "mcp_server.server:app", "--port", "8000", "--log-level", "warning"],
        "health_url": "http://localhost:8000/health",
    },
    # ── Layer 3: Domain Agent Servers (A2A protocol) ──────────────────────────
    {
        "name": "wellness_agent",
        "cmd": [sys.executable, "-m", "uvicorn", "domain_agents.wellness_server:app", "--port", "9001", "--log-level", "warning"],
        "health_url": "http://localhost:9001/health",
    },
    {
        "name": "learning_agent",
        "cmd": [sys.executable, "-m", "uvicorn", "domain_agents.learning_server:app", "--port", "9002", "--log-level", "warning"],
        "health_url": "http://localhost:9002/health",
    },
    {
        "name": "planner_agent",
        "cmd": [sys.executable, "-m", "uvicorn", "domain_agents.planner_server:app", "--port", "9003", "--log-level", "warning"],
        "health_url": "http://localhost:9003/health",
    },
]


def start_services() -> list[subprocess.Popen]:
    """Launch all services as background subprocesses."""
    procs = []
    for svc in SERVICES:
        log_event("system", f"starting {svc['name']}")
        proc = subprocess.Popen(
            svc["cmd"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        procs.append(proc)
    return procs


def wait_for_health(max_wait_sec: int = 30) -> bool:
    """Poll each service's /health endpoint until all respond or timeout."""
    deadline = time.monotonic() + max_wait_sec
    pending = {svc["name"]: svc["health_url"] for svc in SERVICES}

    while pending and time.monotonic() < deadline:
        for name in list(pending):
            try:
                r = httpx.get(pending[name], timeout=1.0)
                if r.status_code == 200:
                    log_event("system", f"{name} is healthy ✓")
                    del pending[name]
            except Exception:
                pass
        if pending:
            time.sleep(0.5)

    if pending:
        console.print(f"[red]Services failed to start: {list(pending.keys())}[/red]")
        return False
    return True


def stop_services(procs: list[subprocess.Popen]) -> None:
    for proc in procs:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


# ── Display ───────────────────────────────────────────────────────────────────

def render_plan(plan: dict[str, Any]) -> None:
    """Render the final weekend plan as rich terminal panels."""
    # Out-of-scope inputs are rejected before the pipeline runs
    if plan.get("out_of_scope"):
        console.print()
        console.print(Panel(
            plan.get("message", "That request is outside my scope."),
            title="[bold yellow]Out of Scope",
            border_style="yellow",
        ))
        console.print()
        return

    wp = plan.get("weekend_plan", {})
    wh = plan.get("wellness_highlights", {})
    lh = plan.get("learning_highlights", {})

    # Header
    console.print()
    console.rule(f"[bold green]🌟 Your Weekend Plan — {wp.get('label', 'This Weekend')}")
    console.print()

    # Summary
    summary = wp.get("summary", "")
    if summary:
        console.print(Panel(summary, title="[bold cyan]Weekend Overview", border_style="cyan"))
        console.print()

    # Affirmation
    affirmation = wh.get("affirmation", "")
    if affirmation:
        console.print(Panel(f"[italic]{affirmation}[/italic]", title="[bold green]✨ Affirmation", border_style="green"))
        console.print()

    # Saturday + Sunday day panels side by side
    for day_key, day_label in [("saturday", "Saturday"), ("sunday", "Sunday")]:
        day = wp.get(day_key, {})
        date_str = day.get("date", "")
        day_content = _build_day_content(day, day_label, date_str)
        console.print(Panel(day_content, title=f"[bold yellow]{day_label} — {date_str}", border_style="yellow"))
        console.print()

    # Learning section
    topic = lh.get("topic", "")
    resources = lh.get("resources", [])
    schedule = lh.get("study_schedule", {})
    if topic:
        learning_text = Text()
        learning_text.append(f"Topic: {topic}\n", style="bold")
        learning_text.append(f"Category: {lh.get('category', '').title()}\n\n")

        if schedule:
            learning_text.append("Study Schedule:\n", style="bold")
            for block in schedule.get("blocks", []):
                learning_text.append(f"  • {block.get('time', '')}: ", style="cyan")
                learning_text.append(f"{block.get('activity', '')} ({block.get('duration_min', 0)} min)\n")
                notes = block.get("notes", "")
                if notes:
                    learning_text.append(f"    {notes}\n", style="dim")

        if resources:
            learning_text.append("\nTop Resources:\n", style="bold")
            for r in resources[:3]:
                learning_text.append(f"  • [{r.get('type', '').upper()}] ", style="magenta")
                learning_text.append(f"{r.get('title', '')}\n")

        console.print(Panel(learning_text, title="[bold magenta]📚 Learning Plan", border_style="magenta"))
        console.print()

    # Meals
    meals = wh.get("meals", [])
    if meals:
        meal_text = Text()
        for m in meals:
            meal_text.append(f"  • {m.get('name', '')} ", style="bold")
            meal_text.append(f"({m.get('calories', 0)} cal, {m.get('prep_min', 0)} min prep)\n")
            tags = ", ".join(m.get("tags", []))
            if tags:
                meal_text.append(f"    Tags: {tags}\n", style="dim")
        console.print(Panel(meal_text, title="[bold green]🥗 Healthy Meals", border_style="green"))
        console.print()

    # Sleep tips
    sleep_tips = wh.get("sleep_tips", [])
    if sleep_tips:
        tips_text = "\n".join(f"  • {t.get('tip', '')}" for t in sleep_tips[:3])
        console.print(Panel(tips_text, title="[bold blue]💤 Sleep Tips", border_style="blue"))
        console.print()

    console.rule("[dim]Generated by Multi-Agent AI System")


def _build_day_content(day: dict, label: str, date_str: str) -> Text:
    """Format a single day's morning/afternoon/evening blocks as a Rich Text object."""
    text = Text()
    for slot in ["morning", "afternoon", "evening"]:
        block = day.get(slot, {})
        if not block:
            continue
        time_range = block.get("time_range", slot.title())
        activities = block.get("activities", [])
        text.append(f"\n{slot.upper()} ({time_range})\n", style="bold")
        if activities:
            for act in activities:
                name = act.get("name", "Activity") if isinstance(act, dict) else str(act)
                dur = act.get("duration_min", 0) if isinstance(act, dict) else 0
                desc = act.get("description", "") if isinstance(act, dict) else ""
                text.append(f"  • {name}", style="cyan")
                if dur:
                    text.append(f" ({dur} min)", style="dim")
                text.append("\n")
                if desc:
                    text.append(f"    {desc[:80]}{'...' if len(desc) > 80 else ''}\n", style="dim")
        else:
            text.append("  Free time — rest and recharge\n", style="dim italic")
    return text


# ── Main ──────────────────────────────────────────────────────────────────────

async def run_pipeline(user_input: str) -> dict[str, Any]:
    from agents.orchestrator import OrchestratorAgent
    orchestrator = OrchestratorAgent()
    return await orchestrator.run(user_input)


def main():
    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Plan my weekend: I want to relax, stay healthy, and learn something new."
    )

    console.print()
    console.print(Panel(
        f"[bold white]{user_input}[/bold white]",
        title="[bold cyan]User Goal",
        border_style="cyan",
    ))
    console.print()

    log_start("Starting Services")
    procs = start_services()

    try:
        if not wait_for_health():
            console.print("[red]Could not start all services. Check that ports 8000, 8001, 8002 are free.[/red]")
            stop_services(procs)
            sys.exit(1)

        log_event("system", "all services healthy — running pipeline")
        result = asyncio.run(run_pipeline(user_input))

        render_plan(result)

        # Also dump raw JSON for inspection
        console.print()
        raw_json = json.dumps(result, indent=2, default=str)
        console.print(Panel(
            raw_json[:3000] + ("\n... (truncated)" if len(raw_json) > 3000 else ""),
            title="[dim]Raw JSON Output",
            border_style="dim",
        ))

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as exc:
        console.print(f"\n[red]Pipeline error: {exc}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        log_event("system", "shutting down services")
        stop_services(procs)


if __name__ == "__main__":
    main()
