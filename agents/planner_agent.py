"""
PlannerAgent — builds the skeleton time-block schedule for the weekend.

Uses only local MCP tools (no HTTP, no LLM) because planning is purely structural.
Returns a {saturday, sunday} dict that other agents fill in with content.
"""
from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from core.logger import log_event


class PlannerAgent(BaseAgent):
    allowed_tool_names = ["get_current_date", "build_time_blocks"]

    def __init__(self, mcp_base_url: str | None = None):
        super().__init__("planner", mcp_base_url)

    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        """Return the upcoming weekend dates and an empty morning/afternoon/evening skeleton."""
        log_event("planner", "starting", task)
        await self.discover_tools()

        # Step 1: anchor the schedule to real weekend dates
        date_info = await self.mcp_call("get_current_date")

        # Step 2: build an empty morning/afternoon/evening skeleton for each day
        skeleton_saturday = await self.mcp_call("build_time_blocks", {
            "activities": [],
            "duration_hours": 14,
        })
        skeleton_sunday = await self.mcp_call("build_time_blocks", {
            "activities": [],
            "duration_hours": 14,
        })

        result = {
            "weekend_dates": {
                "saturday": date_info.get("upcoming_saturday"),
                "sunday": date_info.get("upcoming_sunday"),
                "label": date_info.get("weekend_label"),
            },
            "schedule_skeleton": {
                "saturday": skeleton_saturday,
                "sunday": skeleton_sunday,
            },
        }

        log_event("planner", "completed", result)
        return result
