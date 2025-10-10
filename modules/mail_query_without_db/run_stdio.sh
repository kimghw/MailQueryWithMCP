#!/bin/bash

# MCP Stdio Server 실행 스크립트

# Set Python path and working directory
export PYTHONPATH=/home/kimghw/IACSGRAPH
cd /home/kimghw/IACSGRAPH

# Use virtual environment python
PYTHON="/home/kimghw/IACSGRAPH/.venv/bin/python3"

# Run the stdio server
exec $PYTHON -m modules.mail_query_without_db.mcp_server_stdio
