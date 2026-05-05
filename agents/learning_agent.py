"""
LearningAgent — finds learning topics and resources for the weekend.

Demonstrates: Ollama for intent extraction → REST tool chain for content fetching.
The agent uses the LLM to figure out *what* to search for, then REST tools to get it.
"""
from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from core.logger import log_event


_CATEGORY_KEYWORDS = {
    "tech": ["tech", "technology", "programming", "coding", "software", "ai", "machine learning", "python", "data"],
    "science": ["science", "physics", "biology", "chemistry", "quantum", "nature", "space", "climate"],
    "arts": ["art", "music", "drawing", "painting", "creative", "photography", "writing", "design"],
    "history": ["history", "historical", "ancient", "civilization", "culture", "war", "politics"],
}


class LearningAgent(BaseAgent):
    allowed_tool_names = [
        "parse_intent",
        "get_learning_topics",
        "get_learning_resources",
        "get_study_schedule",
    ]

    def __init__(self, mcp_base_url: str | None = None):
        super().__init__("learning", mcp_base_url)

    async def run(self, task: dict[str, Any]) -> dict[str, Any]:
        """Extract learning intent via Ollama, then fetch topics, resources, and a study schedule."""
        log_event("learning", "starting", task)
        await self.discover_tools()

        user_input = task.get("user_input", "learn something new")

        # Step 1: Use Ollama via MCP to extract what the user wants to learn
        intent_result = await self.mcp_call("parse_intent", {"user_input": user_input})
        category = self._resolve_category(intent_result, user_input)
        log_event("learning", f"resolved category: {category}")

        # Step 2: Get topics for that category
        topics = await self.mcp_call("get_learning_topics", {"category": category})
        if not topics:
            topics = await self.mcp_call("get_learning_topics", {"category": "tech"})

        # Step 3: Pick the first topic and get its resources
        primary_topic = topics[0] if topics else {"id": "t2", "name": "Large Language Models Explained"}
        topic_id = primary_topic.get("id", "t2")
        topic_name = primary_topic.get("name", "the selected topic")

        resources = await self.mcp_call("get_learning_resources", {"topic_id": topic_id})

        # Step 4: Get a structured study schedule
        study_schedule = await self.mcp_call("get_study_schedule", {
            "topic": topic_name,
            "available_hours": 4.0,
        })

        result = {
            "category": category,
            "primary_topic": primary_topic,
            "all_topics": topics[:3],
            "resources": resources[:3],
            "study_schedule": study_schedule,
        }

        log_event("learning", "completed", {"topic": topic_name, "resources": len(resources)})
        return result

    def _resolve_category(self, intent_result: Any, user_input: str) -> str:
        """
        Map LLM intent output to one of our four categories.
        Falls back to keyword matching on the raw user input if LLM output is ambiguous.
        """
        # If the LLM returned a dict with a "category" key, use it
        if isinstance(intent_result, dict):
            cat = intent_result.get("category", "").lower()
            if cat in _CATEGORY_KEYWORDS:
                return cat

        # Keyword fallback on raw user input
        lower_input = user_input.lower()
        for category, keywords in _CATEGORY_KEYWORDS.items():
            if any(kw in lower_input for kw in keywords):
                return category

        # Default: tech (most common learning interest)
        return "tech"
