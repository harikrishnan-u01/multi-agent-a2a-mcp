# Architecture Deep Dive

## Two Protocols, Three Layers

This system uses two distinct protocols at different layers. Understanding why each exists is the core lesson.

```
User (CLI / chat.py)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│              ORCHESTRATOR AGENT (Python)            │
│  validate → parse_intent → decompose → synthesize   │
└──────┬──────────────────┬──────────────┬────────────┘
       │   A2A protocol   │              │
       │  (JSON-RPC/HTTP) │              │
       ▼                  ▼              ▼
┌────────────┐   ┌──────────────┐  ┌──────────────┐
│  Planner   │   │  Wellness    │  │  Learning    │
│  Agent     │   │  Agent       │  │  Agent       │
│  :9003     │   │  :9001       │  │  :9002       │
└──────┬─────┘   └──────┬───────┘  └──────┬───────┘
       │                │                 │
       │         MCP protocol             │
       │    (POST /tools/invoke)          │
       └────────────────┼─────────────────┘
                        ▼
        ┌───────────────────────────────┐
        │         MCP SERVER  :8000     │
        │  ToolRegistry dispatches by   │
        │  category: rest/local/ollama  │
        └──────┬──────────┬─────────────┘
               │          │
       ┌───────┘          └───────────────────┐
       ▼                                       ▼
┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
│ Wellness API │  │ Learning API │  │ Ollama  :11434   │
│    :8001     │  │    :8002     │  │ llama3.2 (LLM)   │
│ /activities  │  │ /topics      │  └─────────────────┘
│ /meals       │  │ /resources   │
│ /sleep-tips  │  │ /schedule    │  ┌─────────────────┐
└──────────────┘  └──────────────┘  │  Local Python   │
                                    │  Functions      │
                                    │  (date, math)   │
                                    └─────────────────┘
```

---

## Protocol 1 — A2A (Agent-to-Agent)

**Used between:** Orchestrator → Domain Agents (ports 9001–9003)

A2A is Google's open protocol for agent interoperability. Each domain agent is an independent HTTP service that advertises itself via a standard **Agent Card**.

### Agent Card Discovery

Every domain agent exposes:
```
GET /.well-known/agent.json
```

Response:
```json
{
  "name": "Wellness Agent",
  "description": "Provides relaxation activities, fitness options...",
  "url": "http://localhost:9001",
  "version": "1.0.0",
  "capabilities": { "streaming": false },
  "skills": [
    { "id": "wellness-activities", "name": "Wellness Activities", "tags": ["wellness", "fitness"] },
    { "id": "meal-planning",       "name": "Meal Planning",       "tags": ["meals", "nutrition"] },
    { "id": "sleep-hygiene",       "name": "Sleep Hygiene",       "tags": ["sleep", "recovery"] }
  ]
}
```

Any orchestrator that speaks A2A can discover what this agent does — without reading its source code.

### Task Execution (JSON-RPC 2.0)

The orchestrator sends a task:
```json
POST http://localhost:9001/
{
  "jsonrpc": "2.0",
  "id": "req-abc123",
  "method": "tasks/send",
  "params": {
    "id": "task-abc123",
    "message": {
      "role": "user",
      "parts": [{ "type": "text", "text": "find relaxation activities, fitness options, meals, and sleep tips" }]
    }
  }
}
```

The domain agent processes it via MCP, then responds:
```json
{
  "jsonrpc": "2.0",
  "id": "req-abc123",
  "result": {
    "id": "task-abc123",
    "status": { "state": "completed", "timestamp": "2026-05-03T10:00:00Z" },
    "artifacts": [{
      "name": "result",
      "parts": [{
        "type": "data",
        "data": {
          "activities": { "relaxation": [...], "fitness": [...] },
          "meals": [...],
          "sleep_tips": [...],
          "affirmation": "..."
        }
      }]
    }]
  }
}
```

### Why A2A for this layer?

| Without A2A | With A2A |
|---|---|
| Orchestrator imports agent Python classes | Orchestrator only knows a URL |
| All agents run in one process | Each agent is an independent service |
| Language-locked to Python | Any agent can be Go, Node.js, Java — as long as it speaks A2A |
| Deploy one thing or everything | Each agent can be scaled/deployed independently |
| No standard discovery | `/.well-known/agent.json` — self-describing |

---

## Protocol 2 — MCP (Model Context Protocol)

**Used between:** Domain Agents → MCP Server (port 8000) → Tools

MCP is a unified tool execution layer. Agents never call REST APIs, Python functions, or Ollama directly. They only call MCP.

### Tool Invocation

```
POST http://localhost:8000/tools/invoke
{ "tool_name": "get_wellness_activities", "parameters": { "type": "relaxation" } }
```

Response:
```json
{ "success": true, "result": [...], "duration_ms": 12.4 }
```

The agent doesn't know if `get_wellness_activities` hit an HTTP API, ran a Python function, or called an LLM. The MCP registry decides.

### Tool Registry Dispatch

```python
match tool.category:
    case "rest":   return rest_tools.execute(tool, parameters)   # → httpx → port 8001/8002
    case "local":  return local_tools.execute(tool, parameters)  # → Python function
    case "ollama": return ollama_tools.execute(tool, parameters)  # → Ollama :11434
```

### Config-Driven Registration

All 12 tools are defined in `config/settings.yaml`. No code changes needed to add a tool:

```yaml
tools:
  - name: "get_wellness_activities"
    category: "rest"
    endpoint: "http://localhost:8001/activities"
    parameters:
      type: { type: "string", enum: ["relaxation", "fitness", "mindfulness"] }

  - name: "get_current_date"
    category: "local"
    handler: "mcp_server.tools.local_tools.get_current_date"

  - name: "generate_affirmation"
    category: "ollama"
    system_prompt: "Generate exactly one motivational sentence, max 20 words."
```

### Why MCP for this layer?

| Without MCP | With MCP |
|---|---|
| Each agent hardcodes API URLs + auth | Agents only know tool names |
| Adding a data source = changing agents | Adding a tool = one entry in `settings.yaml` |
| No unified logging | Every call logged with `duration_ms` |
| Swap REST for local function = agent code change | Change `category` in yaml — agents unchanged |

---

## Full Request Trace

```
User: "Plan my weekend: I want to relax and learn something new."
  │
  ├─ OrchestratorAgent._validate_input()   ← heuristic keyword check (no LLM)
  │
  ├─ MCP: parse_intent (ollama)            ← Ollama extracts intent as JSON
  │     returns: { relax: true, wellness: true, learning: true }
  │
  ├─ _decompose_tasks()
  │     → [PlannerAgent, WellnessAgent, LearningAgent]
  │
  ├─ asyncio.gather() — three concurrent A2A calls:
  │
  │   A2A → PlannerAgent :9003
  │     └── MCP: get_current_date  (local)        → today's date + weekend dates
  │     └── MCP: build_time_blocks (local)         → morning/afternoon/evening skeleton
  │
  │   A2A → WellnessAgent :9001
  │     └── MCP: get_wellness_activities (rest→8001) → relaxation activities
  │     └── MCP: get_wellness_activities (rest→8001) → fitness activities
  │     └── MCP: get_meals               (rest→8001) → healthy meals
  │     └── MCP: get_sleep_tips          (rest→8001) → sleep tips
  │     └── MCP: generate_affirmation    (ollama)    → motivational sentence
  │
  │   A2A → LearningAgent :9002
  │     └── MCP: parse_intent            (ollama)    → extract topic category
  │     └── MCP: get_learning_topics     (rest→8002) → topics by category
  │     └── MCP: get_learning_resources  (rest→8002) → books/videos/courses
  │     └── MCP: get_study_schedule      (rest→8002) → time-blocked study plan
  │
  └─ ExecutionAgent (direct Python call — synthesis, not delegation)
       └── MCP: build_time_blocks (local)    → slot activities into schedule
       └── MCP: summarize_plan    (ollama)   → 3-4 sentence friendly summary
       returns: { weekend_plan: {...}, wellness_highlights: {...}, learning_highlights: {...} }
```

---

## Agent Roles

| Agent | Protocol In | Protocol Out | Responsibility |
|---|---|---|---|
| OrchestratorAgent | User text | A2A (sends) | Validate → parse intent → decompose → delegate → synthesize |
| PlannerAgent | A2A (receives) | MCP | Build weekend skeleton with real dates |
| WellnessAgent | A2A (receives) | MCP | Fetch activities, meals, tips + generate affirmation |
| LearningAgent | A2A (receives) | MCP | Extract topic, fetch resources + study schedule |
| ExecutionAgent | Direct Python | MCP | Assemble final plan + LLM summary |

> ExecutionAgent is not an A2A server — it's the synthesis step called directly by the orchestrator after all A2A results are collected.

---

## Adding a New Domain Agent

1. Create `agents/my_agent.py` — subclass `BaseAgent`, set `allowed_tool_names`, implement `run()`
2. Create `domain_agents/my_server.py` — subclass `A2AServer`, write Agent Card, call agent in `process_task()`
3. Add tool definitions to `config/settings.yaml`
4. Add URL to `config/settings.yaml` under `domain_agents:`
5. Add service to `main.py` SERVICES list
6. Wire into `orchestrator._decompose_tasks()` and `_delegate()`

## Replacing Ollama with Claude API

In `core/ollama_client.py`, swap the `httpx` call for `anthropic.Anthropic().messages.create(...)`.
Nothing else changes — agents call `mcp_call("parse_intent", {...})` regardless of what's underneath.

## Replacing Mock APIs with Real APIs

Change `endpoint:` in `config/settings.yaml`. Agents are unaffected.
