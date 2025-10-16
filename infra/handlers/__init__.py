"""MCP Handlers Module

This module provides reusable MCP handler classes that can be mixed into
different MCP servers using multiple inheritance (Mixin pattern).

Available Handlers:
- AuthHandlers: Authentication and account management tools
- AttachmentFilterHandlers: Attachment filtering and saving tools

Usage:
    from infra.handlers import AuthHandlers, AttachmentFilterHandlers

    class MyMCPHandlers(AuthHandlers, AttachmentFilterHandlers):
        def __init__(self):
            super().__init__()
            # Add your custom tools here
"""

from .base import HandlerProtocol
from .auth_handlers import AuthHandlers
from .attachment_filter_handlers import AttachmentFilterHandlers, AttachmentFilterConfig

__all__ = [
    "HandlerProtocol",
    "AuthHandlers",
    "AttachmentFilterHandlers",
    "AttachmentFilterConfig",
]
