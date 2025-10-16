"""MCP Handler Base Protocol

This module defines the common interface that all MCP handlers should implement.
"""

from typing import Protocol, List, runtime_checkable
from mcp.types import Tool, TextContent


@runtime_checkable
class HandlerProtocol(Protocol):
    """Base protocol that all MCP handlers should implement"""

    def get_tools(self) -> List[Tool]:
        """
        Get list of MCP tools provided by this handler

        Returns:
            List of Tool objects
        """
        ...

    async def handle_tool(self, name: str, arguments: dict) -> List[TextContent]:
        """
        Handle tool call for this handler's tools

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            List of TextContent with results
        """
        ...

    def is_tool(self, tool_name: str) -> bool:
        """
        Check if a tool belongs to this handler

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool belongs to this handler
        """
        ...
