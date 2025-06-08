#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Start the MCP server in the background
# Ensure it logs to stdout/stderr for Docker logs
echo "Starting MCP Server..."
python ./test_mcp_server.py &

# Wait a few seconds for the MCP server to initialize (optional, but can be helpful)
sleep 3

# Start the FastAPI application using Uvicorn
# Bind to 0.0.0.0 to make it accessible from outside the container
echo "Starting FastAPI Uvicorn Server..."
uvicorn api_main:app --host 0.0.0.0 --port 8001 --reload
