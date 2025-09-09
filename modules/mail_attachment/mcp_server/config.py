"""Configuration module for MCP Server"""

import json
import os
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration manager for MCP Server"""
    
    def __init__(self, config_path: str = None):
        self._config = {}
        self._load_config(config_path)
    
    def _load_config(self, config_path: str = None):
        """Load configuration from file"""
        if config_path is None:
            # Check environment variable first
            env_path = os.getenv("MCP_SETTINGS_PATH")
            if env_path:
                config_path = Path(env_path)
            else:
                # Default path relative to this file
                config_path = Path(__file__).parent.parent / "settings.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except FileNotFoundError:
            # Use default configuration if file not found
            self._config = self._get_default_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "paths": {
                "attachments_dir": "./mcp_attachments",
                "log_file": "mcp_mail_attachment_server.log"
            },
            "server": {
                "default_host": "0.0.0.0",
                "default_port": 8002
            },
            "email": {
                "blocked_senders": ["block@krs.co.kr"],
                "default_days_back": 30,
                "default_max_mails": 300,
                "csv_encoding": "utf-8-sig"
            },
            "file_handling": {
                "supported_extensions": [".pdf", ".docx", ".xlsx", ".txt", ".pptx"],
                "max_preview_length": 3000,
                "cleanup_after_query": True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports nested keys with dot notation)"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def attachments_dir(self) -> str:
        """Get attachments directory path"""
        return self.get("paths.attachments_dir", "./mcp_attachments")
    
    @property
    def log_file(self) -> str:
        """Get log file path"""
        return self.get("paths.log_file", "mcp_mail_attachment_server.log")
    
    @property
    def default_host(self) -> str:
        """Get default server host"""
        return self.get("server.default_host", "0.0.0.0")
    
    @property
    def default_port(self) -> int:
        """Get default server port"""
        return int(self.get("server.default_port", 8002))
    
    @property
    def blocked_senders(self) -> list:
        """Get blocked senders list"""
        return self.get("email.blocked_senders", [])
    
    @property
    def default_days_back(self) -> int:
        """Get default days back for email query"""
        return int(self.get("email.default_days_back", 30))
    
    @property
    def default_max_mails(self) -> int:
        """Get default maximum mails to retrieve"""
        return int(self.get("email.default_max_mails", 300))
    
    @property
    def cleanup_after_query(self) -> bool:
        """Get whether to cleanup files after query"""
        return bool(self.get("file_handling.cleanup_after_query", True))


# Singleton instance
_config = None


def get_config(config_path: str = None) -> Config:
    """Get configuration singleton instance"""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config