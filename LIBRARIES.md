# Libraries & Dependencies

All dependencies are listed in `requirements.txt`. Here is what each one does in this project:

---

### FastAPI `fastapi>=0.111.0`

**What it is:** A modern Python web framework for building APIs.

**How it's used here:**
- Powers all three HTTP services: MCP Server (port 8000), Wellness API (port 8001), Learning API (port 8002)
- Each service is a FastAPI `app` with typed route handlers
- Provides automatic request validation via Pydantic and auto-generated OpenAPI docs at `/docs`

```python
# Example from mcp_server/server.py
@app.post("/tools/invoke", response_model=ToolInvokeResponse)
def invoke_tool(request: ToolInvokeRequest):
    return registry.invoke(request)
```

---

### Uvicorn `uvicorn[standard]>=0.29.0`

**What it is:** An ASGI (Asynchronous Server Gateway Interface) server — the thing that actually runs FastAPI apps and listens on a port.

**How it's used here:**
- `main.py` spawns three `uvicorn` subprocesses to run the three FastAPI apps
- The `[standard]` extra includes `watchfiles` (for `--reload`) and `websockets`

```bash
# What main.py does under the hood for each service:
python -m uvicorn mcp_server.server:app --port 8000
```

---

### Pydantic `pydantic>=2.7.0`

**What it is:** A data validation library that uses Python type annotations to define and validate data shapes.

**How it's used here:**
- Defines the wire format for all MCP messages: `ToolDefinition`, `ToolInvokeRequest`, `ToolInvokeResponse`
- Validates every API request and response automatically (FastAPI uses Pydantic internally)
- Defines the data models in mock APIs: `Activity`, `Meal`, `Topic`, `Resource`, etc.

```python
# From mcp_server/tool_types.py
class ToolInvokeRequest(BaseModel):
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
```

If an agent sends a malformed request, Pydantic rejects it with a clear error before it reaches any business logic.

---

### Pydantic-Settings `pydantic-settings>=2.3.0`

**What it is:** A Pydantic extension for reading configuration from environment variables and `.env` files.

**How it's used here:**
- `core/config_loader.py` merges `config/settings.yaml` + `.env` file into a single typed `AppConfig` object
- Environment variables like `OLLAMA_MODEL` and `OLLAMA_BASE_URL` automatically override the YAML defaults

```python
# .env overrides yaml defaults — no code changes needed to switch models
OLLAMA_MODEL=mistral
OLLAMA_BASE_URL=http://localhost:11434
```

---

### HTTPX `httpx>=0.27.0`

**What it is:** A modern HTTP client for Python that supports both synchronous and **async** requests.

**How it's used here:**
- **Async** (`httpx.AsyncClient`): used in `agents/base_agent.py` to call the MCP server from agents (runs in the async event loop)
- **Sync** (`httpx.Client`): used in `mcp_server/tools/rest_tools.py` and `ollama_tools.py` to call APIs from within FastAPI route handlers
- **Sync** (`httpx.get`): used in `main.py` for health-check polling during service startup

Why not `requests`? Because HTTPX supports async, which is essential for running agents concurrently with `asyncio.gather()`.

```python
# Async call in agents (base_agent.py)
async with httpx.AsyncClient(timeout=120.0) as client:
    resp = await client.post(f"{self.mcp_base_url}/tools/invoke", json={...})
```

---

### Rich `rich>=13.7.0`

**What it is:** A library for rich text and beautiful formatting in the terminal — colors, panels, tables, progress bars, and more.

**How it's used here:**
- `core/logger.py` renders every agent event as a colored, timestamped panel — each agent has its own color (orchestrator = white, wellness = green, learning = cyan, etc.)
- `main.py` renders the final weekend plan as structured Rich panels (day-by-day blocks, meals, learning section)
- `scripts/test_mcp.py` renders the smoke test results as a formatted table

```
[14:32:01.443] ORCHESTRATOR › intent parsed
╭────────────────────────────────────╮
│ {                                  │
│   "relax": true,                   │
│   "wellness": true,                │
│   "learning": true                 │
│ }                                  │
╰────────────────────────────────────╯
```

---

### Python-Dotenv `python-dotenv>=1.0.0`

**What it is:** Loads key=value pairs from a `.env` file into environment variables at process startup.

**How it's used here:**
- Called once in `core/config_loader.py` via `load_dotenv()`
- Allows you to store local secrets (like `ANTHROPIC_API_KEY`) in `.env` without hardcoding them
- `.env` is not committed to version control; `.env.example` shows the template

```python
from dotenv import load_dotenv
load_dotenv()  # reads .env → os.environ
```

---

### PyYAML `pyyaml>=6.0.1`

**What it is:** A YAML parser and emitter for Python.

**How it's used here:**
- `core/config_loader.py` reads `config/settings.yaml` to load all server ports, model names, and the full tool definitions list
- The entire tool registry (12 tools with their categories, endpoints, handlers, and system prompts) lives in this YAML file

```python
with open("config/settings.yaml") as f:
    raw = yaml.safe_load(f)   # → Python dict
```

---

### Ollama (external tool, not a pip package)

**What it is:** A tool for running large language models locally on your machine. It exposes a REST API at `http://localhost:11434`.

**How it's used here:**
- `core/ollama_client.py` calls Ollama's `/api/generate` endpoint to get LLM responses
- `mcp_server/tools/ollama_tools.py` calls Ollama synchronously from the MCP server when an `ollama` category tool is invoked
- Used for three tasks: intent parsing (`parse_intent`), plan summarization (`summarize_plan`), and affirmation generation (`generate_affirmation`)
- Default model: `llama3.2` (3.2B parameters, runs on most laptops without a GPU)

```bash
# How agents trigger an LLM call (they don't know it's Ollama):
await self.mcp_call("generate_affirmation", {"theme": "mindfulness"})
# → MCP routes to ollama_tools.execute() → POST http://localhost:11434/api/generate
```

---

### asyncio (Python standard library)

**What it is:** Python's built-in async I/O framework — lets you run multiple coroutines concurrently in a single thread.

**How it's used here:**
- `asyncio.gather()` in `agents/orchestrator.py` runs PlannerAgent, WellnessAgent, and LearningAgent **simultaneously** — all three make their MCP calls in parallel instead of one after another
- All agent `run()` methods and `mcp_call()` are `async def` coroutines
- `main.py` uses `asyncio.run()` to enter the async event loop

```python
# From orchestrator.py — all 3 agents run at the same time
raw_results = await asyncio.gather(
    PlannerAgent().run(task),
    WellnessAgent().run(task),
    LearningAgent().run(task),
)
```

Without `asyncio.gather()`, agents would run sequentially and the pipeline would take 3x longer.

---

### subprocess (Python standard library)

**What it is:** Python's built-in module for spawning and managing child processes.

**How it's used here:**
- `main.py` uses `subprocess.Popen` to launch all three uvicorn servers as background processes
- Captures stderr (for error reporting) while suppressing stdout to keep the terminal clean
- All processes are terminated in a `finally` block when the pipeline finishes

```python
proc = subprocess.Popen(
    ["python", "-m", "uvicorn", "mcp_server.server:app", "--port", "8000"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
)
```
