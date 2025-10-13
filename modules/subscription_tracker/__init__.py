"""Subscription Tracker MCP Server

Automatically tracks subscription-related emails and saves invoice/receipt attachments
to Windows folders via WSL.
"""

from .config import SubscriptionConfig, get_subscription_config

__all__ = ['SubscriptionConfig', 'get_subscription_config']
