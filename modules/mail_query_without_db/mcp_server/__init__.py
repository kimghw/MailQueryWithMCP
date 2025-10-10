"""MCP Server for Mail Attachment

This package contains the modularized MCP server implementation
for handling email attachments.
"""

from .server import HTTPStreamingMailAttachmentServer

__all__ = ["HTTPStreamingMailAttachmentServer"]