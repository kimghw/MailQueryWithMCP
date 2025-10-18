#!/bin/bash
# Unified MCP HTTP Server - Single instance serving multiple MCP servers

# Get the project root directory (2 levels up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Set environment variables
export PYTHONPATH="$PROJECT_ROOT"
export PYTHONDONTWRITEBYTECODE=1

# Default port (can be overridden by environment variable or command line argument)
PORT="${MCP_PORT:-${PORT:-8000}}"
HOST="${MCP_HOST:-0.0.0.0}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--port PORT] [--host HOST]"
            exit 1
            ;;
    esac
done

echo "🚀 Starting Unified MCP Server on $HOST:$PORT"
echo "📧 Mail Query endpoint: http://$HOST:$PORT/mail-query/"
echo "🔐 Enrollment endpoint: http://$HOST:$PORT/enrollment/"

# Run the unified server
exec python3 "$PROJECT_ROOT/entrypoints/production/unified_http_server.py" \
    --host "$HOST" \
    --port "$PORT"
