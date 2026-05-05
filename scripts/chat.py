"""
Interactive Orchestrator REPL — manually test any prompt against the full agent pipeline.

Services start once and stay running across multiple prompts, so each test is fast.
Type any goal, press Enter to run. Type 'quit' or Ctrl+C to exit.

Usage:
    cd agent-mcp
    python3 scripts/chat.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path when running from scripts/
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rich.console import Console
from rich.panel import Panel

from main import render_plan, run_pipeline, start_services, stop_services, wait_for_health

console = Console()

BANNER = """[bold cyan]Orchestrator REPL[/bold cyan]
[dim]Services start once and stay running between prompts.
Type your goal and press Enter. Type [bold]quit[/bold] to exit.[/dim]"""

EXAMPLE_PROMPTS = [
    "Plan my weekend: I want to relax, stay healthy, and learn something new.",
    "I want to go hiking, eat well, and learn about quantum physics.",
    "lazy Sunday — just rest, good food, and maybe some art or music.",
    "I want an active weekend: fitness, healthy eating, and learning Python.",
]


def print_examples() -> None:
    console.print("\n[dim]Example prompts:[/dim]")
    for i, p in enumerate(EXAMPLE_PROMPTS, 1):
        console.print(f"  [dim]{i}.[/dim] {p}")
    console.print()


def main() -> None:
    console.print()
    console.print(Panel(BANNER, border_style="cyan", expand=False))
    print_examples()

    # ── Start services once ────────────────────────────────────────────────
    console.rule("[bold green]Starting Services")
    procs = start_services()

    try:
        if not wait_for_health():
            console.print(
                "[red]Could not start all services. "
                "Check that ports 8000, 8001, 8002 are free.[/red]"
            )
            stop_services(procs)
            sys.exit(1)

        console.print("[green]All services healthy. Ready for input.[/green]\n")

        # ── Prompt loop ────────────────────────────────────────────────────
        while True:
            try:
                user_input = console.input("[bold cyan]>[/bold cyan] ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            if user_input.lower() in {"quit", "exit", "q"}:
                console.print("[dim]Exiting...[/dim]")
                break

            # Allow typing "1"–"4" to pick an example prompt
            if user_input in {"1", "2", "3", "4"}:
                user_input = EXAMPLE_PROMPTS[int(user_input) - 1]
                console.print(f"[dim]Using:[/dim] {user_input}\n")

            console.print()
            console.print(Panel(
                f"[bold white]{user_input}[/bold white]",
                title="[bold cyan]User Goal",
                border_style="cyan",
            ))
            console.print()

            try:
                result = asyncio.run(run_pipeline(user_input))
                render_plan(result)
            except Exception as exc:
                console.print(f"\n[red]Pipeline error:[/red] {exc}")
                import traceback
                traceback.print_exc()

            console.print()
            console.rule("[dim]Ready for next prompt")
            console.print()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
    finally:
        console.rule("[bold red]Shutting Down Services")
        stop_services(procs)
        console.print("[green]Done.[/green]")


if __name__ == "__main__":
    main()
