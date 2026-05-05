#!/bin/bash
# Start all three services in separate background processes.
# Use this for development — main.py manages lifecycle automatically for demos.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."

cd "$ROOT"

echo "Starting Wellness API  → http://localhost:8001"
uvicorn mock_apis.wellness_api:app --port 8001 --reload &
WELLNESS_PID=$!

echo "Starting Learning API  → http://localhost:8002"
uvicorn mock_apis.learning_api:app --port 8002 --reload &
LEARNING_PID=$!

echo "Starting MCP Server    → http://localhost:8000"
uvicorn mcp_server.server:app --port 8000 --reload &
MCP_PID=$!

echo ""
echo "All services started."
echo "  Wellness API PID: $WELLNESS_PID"
echo "  Learning API PID: $LEARNING_PID"
echo "  MCP Server PID:   $MCP_PID"
echo ""
echo "Press Ctrl+C to stop all services."

# Save PIDs for stop_services.sh
echo "$WELLNESS_PID $LEARNING_PID $MCP_PID" > /tmp/agent_mcp_pids.txt

wait
