"""
Wellness Domain Agent — A2A-compliant HTTP server (port 9001).

Architecture position:
  Orchestrator  →[A2A]→  THIS SERVER  →[MCP]→  MCP Server  →  REST APIs / Ollama

Receives a natural-language wellness task via the A2A tasks/send protocol,
delegates execution to WellnessAgent (which calls MCP tools), and returns
the structured result wrapped in an A2A Task artifact.

Agent Card skills:
  • wellness-activities  — relaxation, fitness, mindfulness from REST API
  • meal-planning        — healthy meals from REST API
  • sleep-hygiene        — sleep tips from REST API
  • affirmation          — motivational sentence via Ollama

Run standalone:
    uvicorn domain_agents.wellness_server:app --port 9001
"""
from __future__ import annotations

from typing import Any

from a2a.server import A2AServer
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agents.wellness_agent import WellnessAgent


class WellnessA2AServer(A2AServer):
    def __init__(self):
        card = AgentCard(
            name="Wellness Agent",
            description=(
                "Provides relaxation activities, fitness options, healthy meals, "
                "sleep tips, and motivational affirmations for weekend planning."
            ),
            url="http://localhost:9001",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=False),
            skills=[
                AgentSkill(
                    id="wellness-activities",
                    name="Wellness Activities",
                    description="Find relaxation, fitness, and mindfulness activities via MCP REST tools",
                    tags=["wellness", "fitness", "relaxation", "mindfulness"],
                    examples=["Find relaxation and fitness activities for the weekend"],
                ),
                AgentSkill(
                    id="meal-planning",
                    name="Meal Planning",
                    description="Suggest healthy meals via MCP REST tools",
                    tags=["meals", "nutrition", "healthy-eating"],
                    examples=["Get healthy meal suggestions for the weekend"],
                ),
                AgentSkill(
                    id="sleep-hygiene",
                    name="Sleep Hygiene",
                    description="Provide sleep hygiene tips via MCP REST tools",
                    tags=["sleep", "recovery", "wellness"],
                    examples=["Get sleep improvement tips"],
                ),
                AgentSkill(
                    id="affirmation",
                    name="Motivational Affirmation",
                    description="Generate a wellness affirmation via Ollama through MCP",
                    tags=["motivation", "affirmation", "llm"],
                    examples=["Generate a motivational affirmation for self-care"],
                ),
            ],
        )
        super().__init__(card)

    async def process_task(self, text: str) -> dict[str, Any]:
        agent = WellnessAgent()
        return await agent.run({"goal": text})


_server = WellnessA2AServer()
app = _server.app
