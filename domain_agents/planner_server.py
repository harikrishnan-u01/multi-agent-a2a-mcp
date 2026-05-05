"""
Planner Domain Agent — A2A-compliant HTTP server (port 9003).

Architecture position:
  Orchestrator  →[A2A]→  THIS SERVER  →[MCP]→  MCP Server  →  Local Tools

Receives a scheduling task, runs PlannerAgent which calls only local MCP tools
(get_current_date, build_time_blocks — no HTTP, no LLM), and returns the
weekend schedule skeleton via A2A.

Agent Card skills:
  • schedule-skeleton  — morning/afternoon/evening time blocks for Sat + Sun

Run standalone:
    uvicorn domain_agents.planner_server:app --port 9003
"""
from __future__ import annotations

from typing import Any

from a2a.server import A2AServer
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agents.planner_agent import PlannerAgent


class PlannerA2AServer(A2AServer):
    def __init__(self):
        card = AgentCard(
            name="Planner Agent",
            description=(
                "Builds a morning/afternoon/evening time-block skeleton for the upcoming "
                "Saturday and Sunday. Uses only local MCP tools — no HTTP calls, no LLM."
            ),
            url="http://localhost:9003",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=False),
            skills=[
                AgentSkill(
                    id="schedule-skeleton",
                    name="Weekend Schedule Skeleton",
                    description=(
                        "Build an empty time-block schedule for the upcoming weekend. "
                        "Returns real Saturday/Sunday dates and morning/afternoon/evening slots."
                    ),
                    tags=["planning", "schedule", "time-blocks", "weekend"],
                    examples=["Build a weekend schedule skeleton for this Saturday and Sunday"],
                ),
            ],
        )
        super().__init__(card)

    async def process_task(self, text: str) -> dict[str, Any]:
        agent = PlannerAgent()
        return await agent.run({"goal": text})


_server = PlannerA2AServer()
app = _server.app
