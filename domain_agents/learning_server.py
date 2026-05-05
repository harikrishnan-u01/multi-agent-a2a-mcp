"""
Learning Domain Agent — A2A-compliant HTTP server (port 9002).

Architecture position:
  Orchestrator  →[A2A]→  THIS SERVER  →[MCP]→  MCP Server  →  REST APIs / Ollama

Receives a learning task (with the user's original query embedded in the text),
runs LearningAgent which calls Ollama for intent extraction and REST APIs for
topics/resources/schedule, and returns the structured result via A2A.

Agent Card skills:
  • topic-discovery    — find topics by category (tech/science/arts/history)
  • resource-curation  — books, videos, courses for a topic
  • study-schedule     — time-blocked study plan via REST API

Run standalone:
    uvicorn domain_agents.learning_server:app --port 9002
"""
from __future__ import annotations

from typing import Any

from a2a.server import A2AServer
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agents.learning_agent import LearningAgent


class LearningA2AServer(A2AServer):
    def __init__(self):
        card = AgentCard(
            name="Learning Agent",
            description=(
                "Finds learning topics, curates resources, and builds study schedules "
                "based on the user's interests. Uses Ollama for intent extraction via MCP."
            ),
            url="http://localhost:9002",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=False),
            skills=[
                AgentSkill(
                    id="topic-discovery",
                    name="Topic Discovery",
                    description="Find relevant learning topics by category via MCP REST tools",
                    tags=["learning", "topics", "education"],
                    examples=["Find tech learning topics for the weekend"],
                ),
                AgentSkill(
                    id="resource-curation",
                    name="Resource Curation",
                    description="Find books, videos, and courses for a topic via MCP REST tools",
                    tags=["resources", "books", "courses", "videos"],
                    examples=["Get learning resources for Python programming"],
                ),
                AgentSkill(
                    id="study-schedule",
                    name="Study Schedule",
                    description="Generate a structured time-blocked study plan via MCP REST tools",
                    tags=["schedule", "planning", "study"],
                    examples=["Create a 4-hour study plan for machine learning"],
                ),
            ],
        )
        super().__init__(card)

    async def process_task(self, text: str) -> dict[str, Any]:
        agent = LearningAgent()
        return await agent.run({"goal": text, "user_input": text})


_server = LearningA2AServer()
app = _server.app
