"""
A2AServer — base class for all A2A-compliant domain agent HTTP servers.

Every domain agent subclasses this and implements process_task().
The A2A protocol layer (Agent Card + JSON-RPC routing) is handled here.

Endpoints:
  GET  /.well-known/agent.json  — Agent Card (capabilities, skills, URL)
  GET  /health                  — liveness probe
  POST /                        — JSON-RPC: tasks/send, tasks/get

A2A task lifecycle (synchronous mode used here):
  tasks/send → process_task() runs inline → returns completed Task
  tasks/get  → returns stored Task by ID (for polling clients)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from a2a.types import (
    Artifact, DataPart, JSONRPCError, JSONRPCResponse,
    Message, Task, TaskQueryParams, TaskSendParams,
    TaskState, TaskStatus, TextPart,
)


class A2AServer(ABC):
    def __init__(self, agent_card):
        self.agent_card = agent_card
        self._tasks: dict[str, Task] = {}
        self.app = FastAPI(title=agent_card.name)
        self._register_routes()

    def _register_routes(self) -> None:
        """Bind the health, agent card, and JSON-RPC endpoints to the FastAPI app."""
        app = self.app
        server = self  # capture for closures

        @app.get("/health")
        def health():
            return {"status": "ok", "agent": server.agent_card.name}

        @app.get("/.well-known/agent.json")
        def get_agent_card():
            return server.agent_card.model_dump()

        @app.post("/")
        async def handle_jsonrpc(request: Request):
            body = await request.json()
            method = body.get("method", "")
            req_id = body.get("id", 0)
            params = body.get("params", {})

            try:
                if method == "tasks/send":
                    p = TaskSendParams(**params)
                    result = await server._handle_send(p)
                elif method == "tasks/get":
                    p = TaskQueryParams(**params)
                    result = server._handle_get(p)
                else:
                    return JSONResponse(JSONRPCError(
                        id=req_id,
                        error={"code": -32601, "message": f"Method '{method}' not found"},
                    ).model_dump())
            except Exception as exc:
                return JSONResponse(
                    JSONRPCError(
                        id=req_id,
                        error={"code": -32603, "message": str(exc)},
                    ).model_dump(),
                    status_code=500,
                )

            return JSONResponse(
                JSONRPCResponse(id=req_id, result=result.model_dump()).model_dump()
            )

    async def _handle_send(self, params: TaskSendParams) -> Task:
        """Run tasks/send: call process_task() inline and return a completed (or failed) Task."""
        text = _extract_text(params.message)

        task = Task(
            id=params.id,
            status=TaskStatus(state=TaskState.working, timestamp=_now()),
            history=[params.message],
        )
        self._tasks[params.id] = task

        try:
            result_data = await self.process_task(text)
            task.status = TaskStatus(state=TaskState.completed, timestamp=_now())
            task.artifacts = [Artifact(parts=[DataPart(data=result_data)])]
        except Exception as exc:
            task.status = TaskStatus(
                state=TaskState.failed,
                timestamp=_now(),
                message=Message(role="agent", parts=[TextPart(text=str(exc))]),
            )

        self._tasks[params.id] = task
        return task

    def _handle_get(self, params: TaskQueryParams) -> Task:
        """Run tasks/get: look up a previously sent task by ID."""
        task = self._tasks.get(params.id)
        if not task:
            raise ValueError(f"Task '{params.id}' not found")
        return task

    @abstractmethod
    async def process_task(self, text: str) -> dict[str, Any]:
        """Subclasses implement domain agent logic here. Returns a result dict."""
        ...


def _extract_text(message: Message) -> str:
    for part in message.parts:
        if isinstance(part, TextPart):
            return part.text
    return ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
