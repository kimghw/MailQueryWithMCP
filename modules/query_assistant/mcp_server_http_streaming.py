"""HTTP Streaming MCP Server entry point

This file imports and uses the modular MCP server implementation.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.query_assistant.mcp_server import HTTPStreamingQueryAssistantServer
from modules.query_assistant.config import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    config = get_config()
    
    # Get server configuration
    mcp_config = config.get('mcp_server', {})
    host = mcp_config.get('host', '0.0.0.0')
    port = mcp_config.get('port', 8001)
    
    # Get database configuration
    db_config = config.get('database', {})
    
    # Get vector store configuration
    vector_config = config.get('vector_store', {})
    qdrant_url = vector_config.get('url', 'localhost')
    qdrant_port = vector_config.get('port', 6333)
    
    # Get API key
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    logger.info(f"🚀 Starting MCP Server with configuration from settings.json")
    logger.info(f"   Host: {host}")
    logger.info(f"   Port: {port}")
    logger.info(f"   Qdrant: {qdrant_url}:{qdrant_port}")
    
    # Create and run server
    server = HTTPStreamingQueryAssistantServer(
        db_config=db_config,
        qdrant_url=qdrant_url,
        qdrant_port=qdrant_port,
        openai_api_key=openai_api_key,
        host=host,
        port=port
    )
    
    server.run()


if __name__ == "__main__":
    main()