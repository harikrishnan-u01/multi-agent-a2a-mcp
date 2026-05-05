"""
A2A (Agent-to-Agent) protocol Pydantic models.

Based on the Google A2A open protocol spec (simplified educational subset).
Supports: tasks/send, tasks/get, Agent Card discovery.

Key concepts:
  AgentCard  — advertises an agent's identity, capabilities, and skills
  Task       — the unit of work exchanged between agents
  Message    — a user→agent or agent→user message containing typed Parts
  Part       — TextPart (natural language) or DataPart (structured JSON)
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


# ── Parts ─────────────────────────────────────────────────────────────────────

class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class DataPart(BaseModel):
    type: Literal["data"] = "data"
    data: dict[str, Any]


# Discriminated union — Pydantic picks the right model based on the "type" field
Part = Annotated[Union[TextPart, DataPart], Field(discriminator="type")]


# ── Message ───────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: Literal["user", "agent"]
    parts: list[Part]


# ── Task ──────────────────────────────────────────────────────────────────────

class TaskState(str, Enum):
    submitted = "submitted"
    working = "working"
    completed = "completed"
    failed = "failed"


class TaskStatus(BaseModel):
    state: TaskState
    message: Message | None = None
    timestamp: str = ""


class Artifact(BaseModel):
    name: str = "result"
    parts: list[Part]


class Task(BaseModel):
    id: str
    status: TaskStatus
    artifacts: list[Artifact] = []
    history: list[Message] = []


# ── Agent Card ────────────────────────────────────────────────────────────────

class AgentCapabilities(BaseModel):
    streaming: bool = False
    pushNotifications: bool = False
    stateTransitionHistory: bool = False


class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: list[str] = []
    examples: list[str] = []


class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    capabilities: AgentCapabilities = AgentCapabilities()
    skills: list[AgentSkill] = []


# ── JSON-RPC 2.0 ──────────────────────────────────────────────────────────────

class JSONRPCRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int
    method: str
    params: dict[str, Any] = {}


class JSONRPCResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int
    result: Any


class JSONRPCError(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int
    error: dict[str, Any]


# ── RPC Param models ──────────────────────────────────────────────────────────

class TaskSendParams(BaseModel):
    id: str
    message: Message


class TaskQueryParams(BaseModel):
    id: str
