#!/bin/bash
# Local Development - Subscription Tracker STDIO MCP Server Launch Script
# For Claude Desktop integration

set -e

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Set Python path
export PYTHONPATH="$PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Use virtual environment if exists, otherwise use system python3
if [ -f "$PROJECT_ROOT/.venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python3"
else
    PYTHON="python3"
fi

# Run the stdio server
exec $PYTHON "$PROJECT_ROOT/entrypoints/local/run_subscription_stdio.py"
