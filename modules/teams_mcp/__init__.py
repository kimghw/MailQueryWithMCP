"""
Teams MCP Module
Microsoft Teams integration via MCP protocol
"""

from .handlers import TeamsHandlers
from .teams_handler import TeamsHandler

__all__ = ["TeamsHandlers", "TeamsHandler"]
