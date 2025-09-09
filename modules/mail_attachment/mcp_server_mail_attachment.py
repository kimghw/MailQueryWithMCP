"""HTTP Streaming-based MCP Server for Mail Attachments - Entry Point"""

import logging
import os

from modules.mail_attachment.mcp_server import HTTPStreamingMailAttachmentServer
from modules.mail_attachment.mcp_server.config import get_config


def main():
    """Main entry point"""
    # Get configuration
    config = get_config()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.log_file),
        ],
    )
    
    # Get configuration from environment or use config defaults
    server = HTTPStreamingMailAttachmentServer(
        host=os.getenv("MCP_HOST", config.default_host),
        port=int(os.getenv("MCP_PORT", str(config.default_port)))
    )
    
    # Run the server
    server.run()


if __name__ == "__main__":
    main()