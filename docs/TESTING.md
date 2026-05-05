# Testing Guide

Tests are organized by layer. Start from the bottom (Layer 1) and work up.

---

## Layer 1 — Mock REST APIs

### Wellness API `:8001`

Start: `python3 -m uvicorn mock_apis.wellness_api:app --port 8001`

```bash
curl "http://localhost:8001/activities?type=relaxation"
curl "http://localhost:8001/activities?type=fitness"
curl "http://localhost:8001/activities?type=mindfulness"
curl "http://localhost:8001/meals?goal=healthy"
curl "http://localhost:8001/sleep-tips"
curl "http://localhost:8001/health"
```

Expected: JSON arrays with 3–7 items each.

### Learning API `:8002`

Start: `python3 -m uvicorn mock_apis.learning_api:app --port 8002`

```bash
curl "http://localhost:8002/topics?category=tech"
curl "http://localhost:8002/topics?category=science"
curl "http://localhost:8002/resources?topic_id=t1"
curl "http://localhost:8002/schedule?topic=Python&available_hours=3"
curl "http://localhost:8002/health"
```

---

## Layer 2 — MCP Server

Requires Layer 1 running. Start: `python3 -m uvicorn mcp_server.server:app --port 8000`

### Tool registry

```bash
# List all registered tools (expect 12)
curl http://localhost:8000/tools | python3 -m json.tool

# Health check (shows tools_registered count)
curl http://localhost:8000/health
```

### Invoke each tool category

```bash
# LOCAL — pure Python, no external dependencies
curl -X POST http://localhost:8000/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_current_date", "parameters": {}}'

curl -X POST http://localhost:8000/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "calculate", "parameters": {"expression": "25 * 4 + 10"}}'

# REST — calls Wellness API
curl -X POST http://localhost:8000/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_wellness_activities", "parameters": {"type": "fitness"}}'

# REST — calls Learning API
curl -X POST http://localhost:8000/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_learning_topics", "parameters": {"category": "science"}}'

# OLLAMA — calls local LLM (Ollama must be running)
curl -X POST http://localhost:8000/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "generate_affirmation", "parameters": {"theme": "mindfulness"}}'

curl -X POST http://localhost:8000/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "parse_intent", "parameters": {"user_input": "I want to relax and learn Python"}}'
```

Each response includes `"success": true`, `"result": {...}`, and `"duration_ms"`.

### Automated smoke test (all 12 tools)

With all Layer 1 + Layer 2 services running:

```bash
python3 scripts/test_mcp.py
```

Expected:
```
                     MCP Tool Smoke Tests
┌─────────────────────────┬──────────────────────┬────────────┬──────┐
│ Tool                    │ Description          │ Status     │ ms   │
├─────────────────────────┼──────────────────────┼────────────┼──────┤
│ get_current_date        │ Local: date calc     │ PASS ✓     │ 1    │
│ calculate               │ Local: safe math     │ PASS ✓     │ 0    │
│ get_wellness_activities │ REST: wellness API   │ PASS ✓     │ 12   │
│ generate_affirmation    │ Ollama: affirmation  │ PASS ✓     │ 2841 │
│ parse_intent            │ Ollama: intent parse │ PASS ✓     │ 3104 │
│ ...                     │ ...                  │ ...        │ ...  │
└─────────────────────────┴──────────────────────┴────────────┴──────┘
Results: 12 passed / 0 failed / 12 total
```

---

## Layer 3 — Domain Agent Servers (A2A)

Requires Layers 1 + 2 running. Start each agent server:

```bash
python3 -m uvicorn domain_agents.wellness_server:app --port 9001
python3 -m uvicorn domain_agents.learning_server:app --port 9002
python3 -m uvicorn domain_agents.planner_server:app --port 9003
```

### Agent Card discovery

```bash
# Discover what each agent can do
curl http://localhost:9001/.well-known/agent.json | python3 -m json.tool
curl http://localhost:9002/.well-known/agent.json | python3 -m json.tool
curl http://localhost:9003/.well-known/agent.json | python3 -m json.tool
```

Expected: Agent Card with `name`, `description`, `capabilities`, and `skills` list.

### Send an A2A task

```bash
# Send a task to the Wellness Agent
curl -X POST http://localhost:9001/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "req-1",
    "method": "tasks/send",
    "params": {
      "id": "task-001",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "find relaxation activities and healthy meals"}]
      }
    }
  }' | python3 -m json.tool
```

Expected response structure:
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "id": "task-001",
    "status": { "state": "completed", "timestamp": "..." },
    "artifacts": [{
      "name": "result",
      "parts": [{ "type": "data", "data": { "activities": {...}, "meals": [...] } }]
    }]
  }
}
```

```bash
# Send a task to the Planner Agent
curl -X POST http://localhost:9003/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "req-2",
    "method": "tasks/send",
    "params": {
      "id": "task-002",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "build weekend schedule skeleton"}]
      }
    }
  }' | python3 -m json.tool

# Send a task to the Learning Agent
curl -X POST http://localhost:9002/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "req-3",
    "method": "tasks/send",
    "params": {
      "id": "task-003",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "find learning topics and resources. User query: I want to learn Python"}]
      }
    }
  }' | python3 -m json.tool
```

---

## End-to-End Pipeline

```bash
python3 main.py
```

**Verification checklist:**

- [ ] All 6 services start and show "is healthy ✓" (3 APIs/MCP + 3 domain agents)
- [ ] Orchestrator logs show intent JSON (e.g. `{"relax": true, "wellness": true, ...}`)
- [ ] A2A client logs show `→` and `←` lines for each domain agent call
- [ ] PLANNER, WELLNESS, LEARNING log lines appear interleaved (concurrent A2A calls)
- [ ] MCP calls show `duration_ms` for every tool invocation within domain agents
- [ ] Final plan shows both Saturday and Sunday sections
- [ ] Final plan includes at least one activity, one meal, and one learning resource
- [ ] Rich panels render with distinct colors per agent layer

### Custom inputs to test validation

```bash
# Should produce a plan
python3 main.py "I want to paint, go hiking, and read about history"
python3 main.py "lazy Sunday — rest and maybe learn some Python"

# Should be rejected (out of scope)
python3 main.py "How many planets are there?"
python3 main.py "I am crazy rich."
python3 main.py "Hello!"
```

---

## Verify Ollama

```bash
curl http://localhost:11434/api/generate \
  -d '{"model":"llama3.2","prompt":"Return this JSON exactly: {\"ok\": true}","stream":false}'
```

Expected: JSON with `"response"` containing `{"ok": true}`.
