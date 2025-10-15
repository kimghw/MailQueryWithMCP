#!/usr/bin/env python3
"""Production Deployment - IACS MCP HTTP Server Entry Point

Entry point for production deployment (Render.com, cloud platforms).
Starts the IACS mail management HTTP MCP server.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# MCP stdio 모드가 아님을 명시
os.environ.pop('MCP_STDIO_MODE', None)

from infra.core.logger import get_logger
from modules.mail_iacs.db_service import IACSDBService

logger = get_logger(__name__)


def initialize_database():
    """Initialize IACS database schema"""
    logger.info("📦 Initializing IACS database...")

    try:
        db_service = IACSDBService()
        logger.info("✅ IACS database initialized successfully")

        # Log panel information if exists
        panels = db_service.get_all_panel_info()
        if panels:
            logger.info(f"📋 Found {len(panels)} panel(s) configured")
            for panel in panels:
                logger.info(f"  - {panel.panel_name}: {panel.chair_address}")
        else:
            logger.warning("⚠️  No panels configured yet")

        # Log default panel if set
        default_panel = db_service.get_default_panel_name()
        if default_panel:
            logger.info(f"🎯 Default panel: {default_panel}")
        else:
            logger.warning("⚠️  No default panel set")

    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        # Don't exit - let the server start anyway
        # Database will be created on first use


def main():
    """Main entry point for production IACS server"""
    logger.info("🚀 Starting PRODUCTION IACS MCP HTTP Server...")
    logger.info(f"📁 Project root: {PROJECT_ROOT}")

    # Create data directory for SQLite if it doesn't exist
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    # Get port and host from environment
    port = int(os.getenv("PORT") or os.getenv("IACS_SERVER_PORT") or "8002")
    host = os.getenv("IACS_SERVER_HOST") or "0.0.0.0"

    logger.info(f"🌐 Starting IACS HTTP MCP server...")
    logger.info(f"📍 Port: {port}")
    logger.info(f"📍 Host: {host}")

    # Initialize database
    initialize_database()

    # Set environment variables for http_server.py
    os.environ['IACS_SERVER_PORT'] = str(port)
    os.environ['IACS_SERVER_HOST'] = host
    os.environ['PYTHONPATH'] = str(PROJECT_ROOT)

    # Import and run MCP HTTP server
    from modules.mail_iacs.mcp_server import HTTPStreamingIACSServer

    logger.info("✅ Starting MCP HTTP Streaming server...")
    server = HTTPStreamingIACSServer(host=host, port=port)
    server.run()


if __name__ == "__main__":
    main()
