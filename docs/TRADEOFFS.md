# Architecture Trade-offs: A2A, MCP, and 6-Server Design

This project is intentionally over-engineered for a single-developer Python codebase. The goal is to demonstrate the patterns used in production multi-agent systems so you can recognise when — and when not — to apply them.

**Stack in one line:**
```
User → Orchestrator →[A2A]→ Domain Agents (3) →[MCP]→ MCP Server → REST APIs / Python / Ollama
```

---

## A2A Protocol

**What it does:** Makes each domain agent an independent HTTP service that any orchestrator can call using a standard JSON-RPC protocol, regardless of language or team.

### Pros

| Benefit | Why it matters |
|---|---|
| Language-independent | Orchestrator in Python, wellness agent in Node.js, learning agent in Java — they all communicate over HTTP, not imports |
| Independent deployment | Each agent deploys, scales, and restarts on its own without touching others |
| Self-describing via Agent Card | `GET /.well-known/agent.json` — any caller can discover what the agent does without reading its code |
| Third-party agents | External services (other companies, open-source agents) can plug in if they speak A2A |
| Clean responsibility boundary | Orchestrator owns coordination; agents own domain logic — neither knows the other's internals |
| Standard protocol | Any A2A-compatible orchestrator in the ecosystem can use your agent today |

### Cons

| Cost | Why it hurts |
|---|---|
| 3 extra servers | Ports 9001–9003 must start, stay healthy, and be monitored |
| Network latency per agent call | HTTP round-trip vs. direct Python function call adds tens of milliseconds |
| More failure points | A crashed agent server looks different from a Python exception — harder to trace |
| Zero benefit in single-language projects | If everything is Python on one machine, you're paying the cost with none of the gain |
| Overkill for prototypes | Adding the A2A layer before you have multi-team requirements is premature |

### When to use A2A

- Different teams own different agents
- Agents are written in different languages or frameworks
- You want to expose your agent for others to call (open ecosystem)
- Agents need to be scaled independently under different load patterns

### When to skip A2A

- One team, one language, one deployment
- Agents are tightly coupled to the orchestrator and won't be reused
- Latency matters and every network hop counts
- Building a prototype where simplicity is more important than future flexibility

---

## MCP Protocol

**What it does:** Gives all agents a single, identical interface to call any tool — whether it runs as an HTTP API, a local Python function, or a remote LLM.

### Pros

| Benefit | Why it matters |
|---|---|
| Agents don't know how tools work | `mcp_call("get_wellness_activities")` is the same whether the backend is port 8001, a database, or a CSV file |
| Config-driven tool registration | Add a new tool by editing `settings.yaml` — no agent code changes needed |
| One interface for three execution types | REST APIs, local Python functions, and Ollama LLM calls all look identical to the agent |
| Centralized observability | Every tool call logged in one place with `duration_ms` — easy to spot slow tools |
| Swap implementations safely | Change `category: rest` to `category: local` in yaml — agents are unaffected |
| Standardized error handling | One place to handle timeouts, retries, and error formatting |

### Cons

| Cost | Why it hurts |
|---|---|
| Extra HTTP hop | Agent → MCP Server → Tool vs. Agent → Tool directly adds latency |
| One more service | MCP Server (port 8000) must run and stay healthy |
| Deeper call stack | A failing REST tool requires tracing: agent → MCP → rest_tools → httpx → API |
| Overkill for two tools | If an agent calls two endpoints that never change, MCP is unnecessary indirection |
| Learning curve | New contributors must understand the tool registry before they can add functionality |

### When to use MCP

- Multiple agents share the same tools
- Tool implementations may change over time (swap REST for database, REST for local cache)
- You want centralized logging and observability across all tool calls
- Non-engineers need to add or configure tools without touching Python code

### When to skip MCP

- One agent, one or two tools, no sharing
- Latency is critical — every network hop costs you
- The tool implementation is stable and will never change
- Quick scripts or single-use automation

---

## Overall Architecture — 6 Servers

### Pros

| Benefit | Why it matters |
|---|---|
| Independently testable layers | You can test the REST APIs without MCP, MCP without agents, agents without the orchestrator |
| Failure isolation | A crashed Learning Agent doesn't take down Wellness or Planner |
| Mirrors real microservice deployments | Each service maps to what would be a separate container or pod in production |
| Swap any layer freely | Replace mock APIs with real ones — nothing above or below changes |
| Realistic observability | Health checks, per-service logging, and startup sequencing reflect production practice |

### Cons

| Cost | Why it hurts |
|---|---|
| 6 processes on your laptop | Memory, CPU, and startup time multiply |
| Longer startup | Health-polling 6 services adds seconds before any work begins |
| More to debug | "Which of the 6 services failed?" is the first question every time |
| Over-provisioned for a CLI tool | A weekend planner doesn't need microservice-level isolation |
| Harder to run in CI | 6 services in a test environment needs real infrastructure or mocking |

---

## Side-by-Side Comparison

| Approach | Servers | Coupling | Language Flexibility | Best Fit |
|---|---|---|---|---|
| Orchestrator calls agent classes directly | 3 | High | Python only | Solo project, prototype, learning MCP |
| Orchestrator → MCP → Tools directly | 3 | Medium | Python only | Single team, tool flexibility needed |
| Orchestrator → A2A → Agent → MCP → Tools | 6 | Low | Any language | Multi-team, multi-language, production |

---

## Honest Summary

| Question | Answer |
|---|---|
| Is A2A necessary in this project? | No. The orchestrator could call MCP directly with 3 servers and identical output. |
| Does A2A add real value here? | Only educational value — you learn the protocol used in real multi-agent production systems. |
| When does A2A earn its complexity? | When agents are owned by different teams or written in different languages. |
| Is MCP necessary in this project? | More justifiable — multiple agents share the same tools, and the config-driven registry is genuinely useful. |
| What's the right architecture for a real production multi-agent system? | Orchestrator → A2A → Agents → MCP → Tools, exactly as built here. |
| What's the right architecture for a solo weekend project? | Orchestrator → Agent classes → MCP → Tools (3 servers, same MCP benefits, no A2A overhead). |

**The core rule:** Use A2A when you have a team/language boundary to cross. Use MCP when you have tools to decouple from agent code. Use both when you have both problems.
