# Entrypoints Directory

This directory contains all entry points for running the MCP Mail Query Server in different environments.

## 📁 Directory Structure

```
entrypoints/
├── configs/            # Configuration files
│   ├── local/         # Local development configs
│   │   └── claude_desktop_config.json
│   └── production/    # Production deployment configs
│       └── render.yaml
│
├── local/              # Local development entry points
│   ├── run_stdio.py   # STDIO server for Claude Desktop
│   ├── run_stdio.sh   # Shell wrapper for STDIO server
│   ├── run_http.py    # HTTP server for local testing
│   └── run_http.sh    # Shell wrapper for HTTP server
│
└── production/         # Production deployment entry points
    ├── start.py       # Main production entry point
    └── start.sh       # Production startup script
```

## 🚀 Usage

### Local Development

#### STDIO Server (for Claude Desktop)
```bash
# Direct Python execution
python3 entrypoints/local/run_stdio.py

# Via shell script (recommended)
./entrypoints/local/run_stdio.sh
```

#### HTTP Server (for local testing)
```bash
# Direct Python execution
python3 entrypoints/local/run_http.py --port 8002 --host 127.0.0.1

# Via shell script (recommended)
./entrypoints/local/run_http.sh 8002 127.0.0.1
```

### Production Deployment

#### Render.com / Cloud Platforms
```bash
# Direct Python execution
python3 entrypoints/production/start.py

# Via shell script (used by render.yaml)
./entrypoints/production/start.sh
```

## 📝 Configuration

### Local Environment
- Config files: `entrypoints/configs/local/`
- Claude Desktop: `entrypoints/configs/local/claude_desktop_config.json`
- Logs: `logs/local/`

### Production Environment
- Config files: `entrypoints/configs/production/`
- Deployment: `entrypoints/configs/production/render.yaml`
- Environment variables: Set via platform

## 🔧 Environment Variables

### Local Development
- `MCP_PORT`: HTTP server port (default: 8002)
- `MCP_HOST`: HTTP server host (default: 127.0.0.1)

### Production
- `PORT`: Server port (provided by platform)
- `MCP_HOST`: Server host (default: 0.0.0.0)
- `ACCOUNT_*_*`: Account configuration variables

## ⚙️ Technical Details

All entry points:
- Set `PYTHONPATH` to project root
- Support both system Python and virtual environment
- Handle logging appropriately for their mode
- Import business logic from `modules/mail_query_without_db/`

No business logic exists in entry points - they are thin wrappers that:
1. Configure the environment
2. Set up logging
3. Import and run the actual server code
