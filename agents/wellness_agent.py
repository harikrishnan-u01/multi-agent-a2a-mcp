"""
WellnessAgent — fetches health and wellness content for the weekend plan.

Demonstrates mixing REST tools (mock APIs) and Ollama tools (generative) through MCP.
All 5 tool calls look identical from the agent's perspective.
"""
from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from core.logger import log_event


class WellnessAgent(BaseAgent):
    allowed_tool_names = [
        "get_wellness_activities",
        "get_meals",
        "get_sleep_tips",
        "generate_affirmation",
    ]

    def __init__(self, mcp_base_url: str | None = None):
        super().__init__("wellness", mcp_base_url)

    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        """Fetch wellness activities, meals, sleep tips, and an LLM-generated affirmation via MCP."""
        log_event("wellness", "starting", task)
        await self.discover_tools()

        # Fetch relaxation and fitness activities in parallel is possible but
        # we keep sequential calls here to make the log output readable
        relaxation = await self.mcp_call("get_wellness_activities", {"type": "relaxation"})
        fitness = await self.mcp_call("get_wellness_activities", {"type": "fitness"})
        mindfulness = await self.mcp_call("get_wellness_activities", {"type": "mindfulness"})
        meals = await self.mcp_call("get_meals", {"goal": "healthy"})
        sleep_tips = await self.mcp_call("get_sleep_tips")

        # Generative call — Ollama creates a motivational affirmation
        affirmation = await self.mcp_call("generate_affirmation", {"theme": "relaxation, fitness, and self-care"})

        # Pick the top 2 activities from each type to avoid overwhelming the plan
        result = {
            "activities": {
                "relaxation": relaxation[:2],
                "fitness": fitness[:2],
                "mindfulness": mindfulness[:2],
            },
            "meals": meals[:3],
            "sleep_tips": sleep_tips[:4],
            "affirmation": affirmation,
        }

        log_event("wellness", "completed", {"activities_count": 6, "meals_count": len(result["meals"])})
        return result
