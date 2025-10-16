"""MCP Handlers Module

This module provides reusable MCP handler classes that can be mixed into
different MCP servers using multiple inheritance (Mixin pattern).

Available Handlers:
- AuthHandlers: Authentication and account management tools

Usage:
    from infra.handlers import AuthHandlers

    class MyMCPHandlers(AuthHandlers):
        def __init__(self):
            super().__init__()
            # Add your custom tools here
"""

from .base import HandlerProtocol
from .auth_handlers import AuthHandlers

__all__ = [
    "HandlerProtocol",
    "AuthHandlers",
]
