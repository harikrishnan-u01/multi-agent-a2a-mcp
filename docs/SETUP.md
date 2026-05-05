# Setup & Running

## Prerequisites

**1. Python 3.10+**
```bash
python3 --version
```

**2. Ollama with llama3.2**
```bash
# Install from https://ollama.com/download, then:
ollama pull llama3.2       # one-time ~2 GB download
ollama serve               # keep running in a separate terminal
```

**3. Ports free**
```bash
lsof -i :8000 -i :8001 -i :8002 -i :9001 -i :9002 -i :9003
# No output = all ports are free
```

---

## Installation

```bash
# 1. Navigate to project root
cd agent-mcp

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional — defaults work out of the box)
cp .env.example .env
```

Only edit `.env` if you use a different Ollama model or a non-default port:
```bash
OLLAMA_MODEL=llama3.2        # or mistral, llama3.1, etc.
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Running the Full Pipeline (One Command)

```bash
python3 main.py
```

This single command starts all 6 services, runs the pipeline, renders the plan, then shuts everything down:

```
Layer 1 — Mock REST APIs  :8001 :8002
Layer 2 — MCP Server      :8000
Layer 3 — Domain Agents   :9001 :9002 :9003  ← A2A servers (new)
```

**With a custom goal:**
```bash
python3 main.py "I want to paint, go hiking, and read about history"
python3 main.py "lazy Sunday — rest and maybe learn some Python"
```

---

## Interactive Testing (REPL)

Start services once and test multiple prompts without restarting:

```bash
python3 scripts/chat.py
```

```
> Plan my weekend: I want to relax and learn something new.
... plan renders ...
> I want to go hiking and read about ancient civilizations
... new plan renders (services still running, fast) ...
> quit
Services shut down.
```

Type `1`–`4` to pick an example prompt. Type `quit` to exit.

---

## Running Services Individually (Development)

Useful when you want to inspect or develop a single layer.

**Layer 1 — Mock REST APIs**
```bash
# Terminal 1
python3 -m uvicorn mock_apis.wellness_api:app --port 8001 --reload
# http://localhost:8001/docs

# Terminal 2
python3 -m uvicorn mock_apis.learning_api:app --port 8002 --reload
# http://localhost:8002/docs
```

**Layer 2 — MCP Server** (requires Layer 1 running for REST tools)
```bash
# Terminal 3
python3 -m uvicorn mcp_server.server:app --port 8000 --reload
# http://localhost:8000/docs
```

**Layer 3 — Domain Agent Servers** (requires Layer 2 running)
```bash
# Terminal 4
python3 -m uvicorn domain_agents.wellness_server:app --port 9001 --reload

# Terminal 5
python3 -m uvicorn domain_agents.learning_server:app --port 9002 --reload

# Terminal 6
python3 -m uvicorn domain_agents.planner_server:app --port 9003 --reload
```

The `--reload` flag restarts a service automatically when you save a file.

---

## Troubleshooting

**Ollama not responding:**
```bash
ollama serve
ollama list                          # check downloaded models
ollama pull llama3.2                 # download if missing
curl http://localhost:11434/api/tags # verify it's running
```

**Port already in use:**
```bash
lsof -i :8000                        # find the PID using the port
kill -9 <PID>
# Or kill all leftover uvicorn processes at once:
pkill -f "uvicorn.*:800"
pkill -f "uvicorn.*:900"
```

**"Module not found" errors:**
```bash
cd agent-mcp          # must be in project root
source .venv/bin/activate
python3 main.py
```

**Pipeline is very slow (Ollama):**
```bash
ollama pull llama3.2:1b    # smaller, faster model
# In .env:
OLLAMA_MODEL=llama3.2:1b
```

**LLM returns garbled JSON:**
The system has automatic fallback — it strips markdown fences and finds the first valid JSON object. If `parse_intent` still fails, the orchestrator uses safe defaults `{relax: true, wellness: true, learning: true}` and continues.

**Services not starting:**
Check if a previous run left services orphaned:
```bash
pkill -f uvicorn
python3 main.py
```
