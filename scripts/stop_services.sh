#!/bin/bash
# Stop all services started by start_services.sh

if [ -f /tmp/agent_mcp_pids.txt ]; then
    read -r PIDS < /tmp/agent_mcp_pids.txt
    for PID in $PIDS; do
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "Stopped PID $PID"
        fi
    done
    rm /tmp/agent_mcp_pids.txt
    echo "All services stopped."
else
    echo "No PID file found. Services may already be stopped."
    # Fallback: kill any uvicorn processes on our ports
    pkill -f "uvicorn.*:800[012]" 2>/dev/null && echo "Killed uvicorn processes." || true
fi
