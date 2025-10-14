#!/bin/bash
# Local Development - IACS Mail STDIO MCP Server Launch Script
# For Claude Desktop integration

set -e

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Set Python path
export PYTHONPATH="$PROJECT_ROOT"
cd "$PROJECT_ROOT"

# MCP stdio 모드 - stdout은 JSON-RPC 전용
# 모든 로깅을 stderr로 강제 리다이렉트
export PYTHONUNBUFFERED=1
export NO_COLOR=1
export TERM=dumb

# Use virtual environment if exists, otherwise use system python3
if [ -f "$PROJECT_ROOT/.venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python3"
else
    PYTHON="python3"
fi

# Run the IACS stdio server
# Python의 stdout을 그대로 유지하되, 모든 print/로그는 stderr로 리다이렉트
exec $PYTHON "$PROJECT_ROOT/modules/mail_iacs/entrypoints/stdio_server.py"
