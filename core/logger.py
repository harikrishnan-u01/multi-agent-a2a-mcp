"""
Rich-based structured logger. Each agent layer gets a distinct color.
All orchestration events are rendered as labeled panels so the flow is easy to follow.
"""
from __future__ import annotations

import json
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from core.config_loader import get_config

console = Console()

_DEFAULT_COLORS = {
    "orchestrator": "bold white",
    "planner": "blue",
    "wellness": "green",
    "learning": "cyan",
    "execution": "yellow",
    "mcp": "magenta",
    "system": "bold dim white",
}


def _color(agent: str) -> str:
    cfg = get_config()
    colors = {**_DEFAULT_COLORS, **cfg.logging.agent_colors}
    return colors.get(agent.lower(), "white")


def log_event(agent: str, event: str, detail: str | dict | list | None = None) -> None:
    """Log a single orchestration event with optional detail payload."""
    cfg = get_config()
    color = _color(agent)
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    header = Text()
    header.append(f"[{ts}] ", style="dim")
    header.append(f"{agent.upper()}", style=color)
    header.append(f" › {event}", style="white")

    if detail is not None and cfg.logging.show_json_payloads:
        if isinstance(detail, (dict, list)):
            body = json.dumps(detail, indent=2, default=str)
        else:
            body = str(detail)
        panel = Panel(body, title=header, border_style=color.replace("bold ", ""), expand=False)
        console.print(panel)
    else:
        console.print(header)


def log_start(message: str) -> None:
    """Print a green horizontal rule to mark the start of a pipeline phase."""
    console.rule(f"[bold green]{message}")


def log_end(message: str) -> None:
    """Print a blue horizontal rule to mark the end of a pipeline phase."""
    console.rule(f"[bold blue]{message}")


def log_error(agent: str, message: str, exc: Exception | None = None) -> None:
    """Print a red error panel with optional exception detail."""
    detail = f"{message}\n{exc}" if exc else message
    panel = Panel(detail, title=f"[bold red]ERROR › {agent.upper()}", border_style="red", expand=False)
    console.print(panel)
