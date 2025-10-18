#!/bin/bash
# Unified MCP Server Start Script for Render.com
# This script starts the unified HTTP server using uv

set -e

echo "🚀 Starting Unified MCP Server on Render.com"

# Get PORT from environment variable (Render.com sets this automatically)
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "📍 Server will bind to ${HOST}:${PORT}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Verify Python version
echo "🐍 Python version:"
python3 --version

# Install dependencies using uv
echo "📦 Installing dependencies with uv..."
uv pip install -r requirements.txt

# Set environment variables
export PYTHONPATH=/opt/render/project/src:$PYTHONPATH
export PYTHONDONTWRITEBYTECODE=1

# Verify environment
echo "✅ Environment check:"
echo "  - PYTHONPATH: $PYTHONPATH"
echo "  - Working directory: $(pwd)"
echo "  - Database directory: data/"

# Create data directory if it doesn't exist
mkdir -p data

# Start the server
echo "🔥 Starting Unified MCP HTTP Server..."
python3 entrypoints/production/unified_http_server.py \
    --host "$HOST" \
    --port "$PORT"
