# Query Assistant MCP Server

This directory contains the refactored MCP (Model Context Protocol) server implementation for the Query Assistant module.

## Structure

```
mcp_server/
├── __init__.py          # Package initialization
├── server.py            # Main server infrastructure
├── handlers.py          # MCP protocol handlers
├── tools.py             # Query tools implementation
├── prompts.py           # Query prompts implementation
├── utils.py             # Utility functions
└── README.md            # This file
```

## Components

### server.py
- `HTTPStreamingQueryAssistantServer`: Main server class that handles:
  - HTTP streaming communication
  - Session management
  - Request routing
  - Authentication checks
  - Server initialization

### handlers.py
- `MCPHandlers`: Handles MCP protocol methods:
  - Tool listing and execution
  - Prompt listing and retrieval
  - Mail data refresh management
  - Request/response coordination

### tools.py
- `QueryTools`: Implements MCP tools:
  - `simple_query`: Basic query execution
  - `query`: Legacy query with options
  - `query_with_llm_params`: Enhanced query with LLM parameters
- `EnhancedQueryRequest`: Data model for enhanced queries

### prompts.py
- `QueryPrompts`: Manages MCP prompts:
  - Prompt listing
  - System prompt loading
  - Prompt message generation

### utils.py
- Utility functions:
  - `preprocess_arguments`: Clean and normalize input arguments
  - `format_query_result`: Format standard query results
  - `format_enhanced_result`: Format enhanced query results with LLM contributions

## Usage

The server is started via the main entry point:

```python
python -m modules.query_assistant.mcp_server_http_streaming
```

Configuration is read from `settings.json` in the parent directory.

## Port Configuration

Default port: 8001 (configurable in settings.json)

## Dependencies

- MCP SDK
- Starlette (web framework)
- Uvicorn (ASGI server)
- Query Assistant module
- Mail Data Refresher module