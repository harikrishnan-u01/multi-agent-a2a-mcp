"""
ExecutionAgent — assembles the final structured weekend plan.

Takes the raw outputs from PlannerAgent, WellnessAgent, and LearningAgent
and produces a single, coherent JSON plan with an LLM-generated summary.

This agent is the "glue" — it does no independent data fetching.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent
from core.logger import log_event


class ExecutionAgent(BaseAgent):
    allowed_tool_names = ["build_time_blocks", "summarize_plan"]

    def __init__(self, mcp_base_url: str | None = None):
        super().__init__("execution", mcp_base_url)

    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        """Assemble and return the final weekend plan from planner, wellness, and learning results."""
        log_event("execution", "assembling final plan", None)
        await self.discover_tools()

        planner = task.get("planner_result", {})
        wellness = task.get("wellness_result", {})
        learning = task.get("learning_result", {})

        weekend_dates = planner.get("weekend_dates", {})

        # Build Saturday's activities list for time-blocking
        saturday_activities = self._collect_saturday_activities(wellness, learning)
        sunday_activities = self._collect_sunday_activities(wellness, learning)

        saturday_blocks = await self.mcp_call("build_time_blocks", {
            "activities": saturday_activities,
            "duration_hours": 14,
        })
        sunday_blocks = await self.mcp_call("build_time_blocks", {
            "activities": sunday_activities,
            "duration_hours": 14,
        })

        # Summarize the full plan using Ollama
        plan_summary_input = self._build_summary_input(wellness, learning, weekend_dates)
        summary = await self.mcp_call("summarize_plan", {"plan_data": plan_summary_input})

        final_plan = {
            "weekend_plan": {
                "label": weekend_dates.get("label", "This Weekend"),
                "summary": summary,
                "saturday": {
                    "date": weekend_dates.get("saturday"),
                    **saturday_blocks,
                },
                "sunday": {
                    "date": weekend_dates.get("sunday"),
                    **sunday_blocks,
                },
            },
            "wellness_highlights": {
                "activities": wellness.get("activities", {}),
                "meals": wellness.get("meals", []),
                "sleep_tips": wellness.get("sleep_tips", []),
                "affirmation": wellness.get("affirmation", ""),
            },
            "learning_highlights": {
                "topic": learning.get("primary_topic", {}).get("name", ""),
                "category": learning.get("category", ""),
                "resources": learning.get("resources", []),
                "study_schedule": learning.get("study_schedule", {}),
            },
            "generated_at": datetime.now().isoformat(),
        }

        log_event("execution", "plan assembled", {"days": 2, "activities_saturday": len(saturday_activities)})
        return final_plan

    def _collect_saturday_activities(self, wellness: dict, learning: dict) -> list[dict]:
        """Return Saturday's activity list: relaxation + fitness + one learning session."""
        activities = []
        # Saturday: relaxation + mindfulness + morning fitness
        acts = wellness.get("activities", {})
        activities.extend(self._simplify_activities(acts.get("relaxation", [])[:1]))
        activities.extend(self._simplify_activities(acts.get("fitness", [])[:1]))

        # Add a learning session
        topic = learning.get("primary_topic", {})
        if topic:
            activities.append({
                "name": f"Learning: {topic.get('name', 'New Topic')}",
                "duration_min": 90,
                "time_of_day": "afternoon",
                "description": topic.get("description", ""),
            })
        return activities

    def _collect_sunday_activities(self, wellness: dict, learning: dict) -> list[dict]:
        """Return Sunday's activity list: mindfulness + relaxation + study schedule blocks."""
        activities = []
        acts = wellness.get("activities", {})
        activities.extend(self._simplify_activities(acts.get("mindfulness", [])[:1]))
        activities.extend(self._simplify_activities(acts.get("relaxation", [])[1:2]))

        # Add study schedule blocks
        schedule = learning.get("study_schedule", {})
        for block in (schedule.get("blocks") or [])[:2]:
            activities.append({
                "name": block.get("activity", "Study Session"),
                "duration_min": block.get("duration_min", 40),
                "time_of_day": "morning" if "1" in block.get("time", "") else "afternoon",
                "description": block.get("notes", ""),
            })
        return activities

    def _simplify_activities(self, acts: list) -> list[dict]:
        """Normalize activity dicts to only the fields build_time_blocks needs."""
        result = []
        for a in acts:
            if isinstance(a, dict):
                result.append({
                    "name": a.get("name", "Activity"),
                    "duration_min": a.get("duration_min", 30),
                    "time_of_day": a.get("time_of_day", ""),
                    "description": a.get("description", ""),
                })
        return result

    def _build_summary_input(self, wellness: dict, learning: dict, dates: dict) -> str:
        """Build a concise natural-language description of the plan to feed to the LLM summarizer."""
        topic = learning.get("primary_topic", {}).get("name", "a new topic")
        acts = wellness.get("activities", {})
        relax_names = [a.get("name") for a in acts.get("relaxation", []) if isinstance(a, dict)]
        fitness_names = [a.get("name") for a in acts.get("fitness", []) if isinstance(a, dict)]
        label = dates.get("label", "this weekend")

        return (
            f"Weekend: {label}. "
            f"Relaxation: {', '.join(relax_names)}. "
            f"Fitness: {', '.join(fitness_names)}. "
            f"Learning topic: {topic}. "
            f"Healthy meals and sleep hygiene tips included."
        )
