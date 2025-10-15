"""Authentication Infrastructure Module

Provides common authentication handlers and management for MCP servers.

Usage:
    from infra.auth import AuthHandlers

    class MyMCPHandlers(AuthHandlers):
        def __init__(self):
            super().__init__()
            # Add your custom tools here
"""

from .mcp_handlers import AuthHandlers
from .auth_manager import AuthManager

__all__ = ["AuthHandlers", "AuthManager"]
