"""
OrchestratorAgent — the top-level coordinator.

Pipeline:
  1. validate_input → reject off-topic requests before spending LLM budget
  2. parse_intent   → use Ollama (via MCP) to extract sub-goals from free text
  3. decompose      → map goals to domain agent task specs
  4. gather         → send tasks to domain agents via A2A protocol (concurrent)
  5. synthesize     → pass results to ExecutionAgent for final assembly

Protocol layers:
  Orchestrator → Domain Agents : A2A (JSON-RPC over HTTP, ports 9001–9003)
  Domain Agents → MCP Server   : MCP (POST /tools/invoke, port 8000)
  MCP Server → Tools           : REST APIs / local functions / Ollama
"""
from __future__ import annotations

import asyncio
import re
from typing import Any

from a2a.client import A2AClient
from agents.base_agent import BaseAgent
from agents.execution_agent import ExecutionAgent
from core.config_loader import get_config
from core.logger import log_event, log_end, log_start

# Words that indicate a weekend/lifestyle planning request (whole-word matched)
_PLANNING_KEYWORDS = {
    "plan", "weekend", "relax", "relaxation", "rest", "recharge",
    "health", "healthy", "wellness", "fitness", "exercise", "workout",
    "yoga", "meditation", "hike", "hiking", "walk", "run", "swim",
    "eat", "meal", "food", "cook", "diet", "sleep",
    "learn", "study", "read", "explore", "create", "paint", "draw",
    "music", "hobby", "activity", "activities", "saturday", "sunday", "schedule",
}

# Phrases that express personal intent/desire (substring matched — word boundaries included)
_INTENT_PHRASES = re.compile(
    r"\b(i want|i'd like|i would like|i need|i feel like|i'm thinking|"
    r"help me|suggest|give me|let's|lets|make me a|create a|"
    r"can you plan|can you suggest|how about|what about)\b",
    re.IGNORECASE,
)


def _out_of_scope_response(user_input: str) -> dict:
    return {
        "out_of_scope": True,
        "message": (
            f'"{user_input.strip()}" doesn\'t look like a weekend planning request.\n\n'
            "I'm a Weekend Planner — I can help you plan activities, meals, fitness, "
            "and learning for your weekend.\n\n"
            "Try something like:\n"
            '  • "Plan my weekend: I want to relax and learn something new."\n'
            '  • "I want an active Saturday with hiking and healthy food."\n'
            '  • "Help me plan a creative and restful Sunday."'
        ),
    }


class OrchestratorAgent(BaseAgent):
    allowed_tool_names = ["parse_intent"]

    def __init__(self, mcp_base_url: str | None = None):
        super().__init__("orchestrator", mcp_base_url)

    async def run(self, user_input: str) -> dict[str, Any]:
        log_start("Agentic AI Pipeline Starting")
        log_event("orchestrator", "received user input", user_input)

        # Step 0: Reject inputs that are clearly not weekend planning requests
        rejection = self._validate_input(user_input)
        if rejection:
            log_event("orchestrator", "input rejected — out of scope", user_input)
            log_end("Pipeline Skipped")
            return rejection

        await self.discover_tools()

        # Step 1: Parse intent — understand what the user wants
        intent = await self._parse_intent(user_input)

        # Step 2: Decompose into domain agent task specs
        tasks = self._decompose_tasks(intent, user_input)
        log_event("orchestrator", "task decomposition", tasks)

        # Step 2b: Guard — if no domain agent would run, the plan will be empty.
        # Checked AFTER decomposition because that's the definitive signal: if the
        # intent mapper produced no domain agents, we have nothing useful to return.
        # This catches "all-false" intent AND recognised-but-unhandled intents (e.g.
        # a future intent key not yet wired into _decompose_tasks).
        domain_agents = [t for t in tasks if t["agent"] != "PlannerAgent"]
        if not domain_agents:
            log_event("orchestrator", "no domain agents identified — rejecting", intent)
            log_end("Pipeline Skipped")
            return _out_of_scope_response(user_input)

        # Step 3: Run domain agents concurrently
        log_event("orchestrator", "launching domain agents concurrently", [t["agent"] for t in tasks])
        results = await self._delegate(tasks, user_input)

        # Step 4: Synthesize results into a final structured plan
        log_event("orchestrator", "synthesizing results with ExecutionAgent")
        final_plan = await self._synthesize(results)

        log_end("Pipeline Complete")
        return final_plan

    def _validate_input(self, user_input: str) -> dict[str, Any] | None:
        """
        Fast heuristic guard — no LLM call, runs before any agent work.

        Opt-in logic: input must contain at least ONE planning signal to proceed.
        A planning signal is either:
          - A planning keyword (whole-word): "relax", "hike", "learn", "weekend", etc.
          - A personal intent phrase: "I want", "help me", "I'd like", "suggest", etc.

        Anything without a planning signal is rejected immediately.
        This catches factual questions ("How many planets?"), statements ("I am rich."),
        greetings ("Hello!"), and other off-topic inputs without wasting an LLM call.
        """
        lower = user_input.lower()

        has_planning_keyword = any(
            re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in _PLANNING_KEYWORDS
        )
        has_intent_phrase = bool(_INTENT_PHRASES.search(lower))

        if has_planning_keyword or has_intent_phrase:
            return None

        return _out_of_scope_response(user_input)

    async def _parse_intent(self, user_input: str) -> dict[str, Any]:
        """
        Use Ollama via MCP to extract structured intent.

        Fallback chain:
          1. LLM result — used when at least one flag is true
          2. Keyword inference — used when LLM returns all-false (it understood the
             JSON format but missed the intent, e.g. "give me what to study")
          3. All-true defaults — used only when the LLM call itself fails
        """
        try:
            result = await self.mcp_call("parse_intent", {"user_input": user_input})
            if isinstance(result, dict) and not result.get("error"):
                if any(result.values()):
                    log_event("orchestrator", "intent parsed", result)
                    return result
                # LLM returned all-false — it parsed the JSON but missed the meaning.
                # Use keyword inference so phrases like "give me what to study" don't
                # silently fall through to an empty plan.
                inferred = self._infer_intent_from_keywords(user_input)
                log_event("orchestrator", "LLM returned all-false — using keyword fallback", inferred)
                return inferred
        except Exception as exc:
            log_event("orchestrator", f"intent parsing failed, using defaults: {exc}")

        # LLM call itself failed — assume common goals
        default = {"relax": True, "wellness": True, "learning": True, "social": False, "creative": False}
        log_event("orchestrator", "using default intent", default)
        return default

    def _infer_intent_from_keywords(self, user_input: str) -> dict[str, bool]:
        """Keyword-based intent inference used when the LLM returns all-false."""
        lower = user_input.lower()
        return {
            "relax":    bool(re.search(r"\b(relax|rest|chill|lazy|unwind|recharge|sleep)\b", lower)),
            "wellness": bool(re.search(r"\b(health|healthy|fitness|yoga|meal|food|cook|workout|exercise|hike|walk|run|swim)\b", lower)),
            "learning": bool(re.search(r"\b(learn|study|read|explore|course|book|topic|research|discover|understand)\b", lower)),
            "social":   bool(re.search(r"\b(meet|social|friend|people|network|connect|hang)\b", lower)),
            "creative": bool(re.search(r"\b(create|paint|draw|music|art|write|craft|design|build)\b", lower)),
        }

    def _decompose_tasks(self, intent: dict[str, Any], user_input: str) -> list[dict[str, Any]]:
        """
        Map intent flags to domain agent task specs.
        Every run always includes PlannerAgent (we always need a schedule skeleton).
        """
        tasks = [{"agent": "PlannerAgent", "goal": "build weekend schedule skeleton"}]

        # Wellness covers physical, mental, social, and creative activity goals
        wellness_triggers = {"relax", "wellness", "fitness", "mindfulness", "health", "social", "creative"}
        if any(intent.get(k) for k in wellness_triggers) or not intent:
            tasks.append({
                "agent": "WellnessAgent",
                "goal": "find relaxation activities, fitness options, meals, and sleep tips",
            })

        # Only include LearningAgent if the LLM explicitly flagged learning intent.
        # Default is False — don't assume learning when it wasn't asked for.
        if intent.get("learning", False):
            tasks.append({
                "agent": "LearningAgent",
                "goal": "find learning topics and resources",
                "user_input": user_input,
            })

        return tasks

    async def _delegate(
        self, tasks: list[dict[str, Any]], user_input: str
    ) -> dict[str, Any]:
        """
        Send tasks to domain agent servers via the A2A protocol.

        Each domain agent is an independent FastAPI service. The orchestrator
        sends a JSON-RPC tasks/send request to each agent's URL and awaits the
        completed Task artifact. asyncio.gather() keeps all three calls concurrent.

        A2A flow per agent:
          POST <agent_url>/  {"method": "tasks/send", "params": {"message": ...}}
          ← Task {status: completed, artifacts: [{parts: [DataPart(data={...})]}]}
        """
        cfg = get_config()
        client = A2AClient()

        agent_url_map = {
            "PlannerAgent":  cfg.domain_agents.planner_url,
            "WellnessAgent": cfg.domain_agents.wellness_url,
            "LearningAgent": cfg.domain_agents.learning_url,
        }

        coroutines = []
        agent_names = []
        for task in tasks:
            agent_name = task["agent"]
            url = agent_url_map.get(agent_name)
            if not url:
                continue
            goal = task.get("goal", "perform your task")
            if agent_name == "LearningAgent":
                # Embed original user query so learning agent can extract topic intent
                message = f"{goal}. User query: {task.get('user_input', user_input)}"
            else:
                message = goal
            coroutines.append(client.send_task(url, message))
            agent_names.append(agent_name)

        log_event("orchestrator", "sending A2A tasks concurrently", {
            name: agent_url_map[name] for name in agent_names
        })

        raw_results = await asyncio.gather(*coroutines, return_exceptions=True)

        results = {}
        for name, result in zip(agent_names, raw_results):
            if isinstance(result, Exception):
                log_event("orchestrator", f"{name} A2A call failed", str(result))
                results[name] = {"error": str(result)}
            else:
                results[name] = result

        return results

    async def _synthesize(self, agent_results: dict[str, Any]) -> dict[str, Any]:
        """Pass all agent outputs to ExecutionAgent for final assembly."""
        execution_agent = ExecutionAgent(self.mcp_base_url)
        return await execution_agent.run({
            "planner_result": agent_results.get("PlannerAgent", {}),
            "wellness_result": agent_results.get("WellnessAgent", {}),
            "learning_result": agent_results.get("LearningAgent", {}),
        })
