"""
A2AClient — async HTTP client for communicating with A2A-compliant agent servers.

The client speaks the A2A JSON-RPC protocol:
  1. POST /  with method "tasks/send" → sends a natural-language task
  2. Extracts the DataPart result from the completed Task artifacts

Usage:
    client = A2AClient()
    result = await client.send_task("http://localhost:9001", "find wellness activities")
    # result is the dict returned by the domain agent
"""
from __future__ import annotations

import uuid
from typing import Any

import httpx

from a2a.types import AgentCard, DataPart, Task, TaskState
from core.logger import log_event


class A2AClient:
    def __init__(self, timeout: float = 120.0):
        self.timeout = timeout

    async def discover(self, agent_url: str) -> AgentCard:
        """Fetch the Agent Card — learn what skills this agent has."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{agent_url.rstrip('/')}/.well-known/agent.json")
            resp.raise_for_status()
            return AgentCard(**resp.json())

    async def send_task(
        self,
        agent_url: str,
        message: str,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a task to a domain agent server via A2A tasks/send.

        The message is wrapped in an A2A Message with a TextPart.
        The agent processes it and returns a completed Task whose
        first artifact DataPart contains the result dict.
        """
        task_id = task_id or uuid.uuid4().hex
        base_url = agent_url.rstrip("/")

        payload = {
            "jsonrpc": "2.0",
            "id": f"req-{task_id[:8]}",
            "method": "tasks/send",
            "params": {
                "id": task_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}],
                },
            },
        }

        log_event(
            "a2a-client",
            f"→ {base_url}  tasks/send",
            {"task_id": task_id[:8], "message": message[:80]},
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(base_url + "/", json=payload)
            resp.raise_for_status()
            body = resp.json()

        if "error" in body:
            raise RuntimeError(f"A2A JSON-RPC error from {base_url}: {body['error']}")

        task = Task(**body["result"])

        if task.status.state == TaskState.failed:
            error_msg = "Task failed"
            if task.status.message:
                for part in task.status.message.parts:
                    if hasattr(part, "text"):
                        error_msg = part.text
                        break
            raise RuntimeError(f"A2A task failed at {base_url}: {error_msg}")

        # Extract the result dict from the first DataPart artifact
        for artifact in task.artifacts:
            for part in artifact.parts:
                if isinstance(part, DataPart):
                    log_event(
                        "a2a-client",
                        f"← {base_url}  task completed",
                        {"task_id": task_id[:8]},
                    )
                    return part.data

        log_event("a2a-client", f"← {base_url}  no DataPart in artifacts", {"task_id": task_id[:8]})
        return {}
