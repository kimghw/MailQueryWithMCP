"""Configuration management for Query Assistant module"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

class Config:
    """Configuration manager for Query Assistant"""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration
        
        Args:
            config_path: Path to settings.json file. If None, uses default location.
        """
        if config_path is None:
            # Default to settings.json in the same directory as this file
            config_path = Path(__file__).parent / "settings.json"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file with environment variable override support"""
        # Load base configuration from file
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            # If no config file, use defaults
            config = self._get_default_config()
        
        # Override with environment variables
        self._apply_env_overrides(config)
        
        return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "database": {
                "default_type": "sqlite",
                "sqlite": {
                    "path": "./data/iacsgraph.db"
                }
            },
            "vector_store": {
                "provider": "qdrant",
                "qdrant": {
                    "url": "localhost",
                    "port": 6333,
                    "collection_name": "query_templates_unified"
                }
            },
            "embedding": {
                "provider": "openai",
                "openai": {
                    "model": "text-embedding-3-large",
                    "dimension": 3072
                }
            },
            "api_server": {
                "host": "0.0.0.0",
                "port": 8000
            },
            "logging": {
                "level": "INFO"
            }
        }
    
    def _apply_env_overrides(self, config: Dict[str, Any]):
        """Apply environment variable overrides to configuration
        
        Uses common environment variables from .env file
        """
        # Database configuration (from .env)
        if os.getenv("DATABASE_PATH"):
            config.setdefault("database", {})["path"] = os.getenv("DATABASE_PATH")
        
        # Vector store configuration (common Qdrant settings)
        config.setdefault("vector_store", {})
        if os.getenv("QDRANT_URL"):
            config["vector_store"]["url"] = os.getenv("QDRANT_URL")
        else:
            config["vector_store"]["url"] = "localhost"  # default
            
        if os.getenv("QDRANT_PORT"):
            config["vector_store"]["port"] = int(os.getenv("QDRANT_PORT"))
        else:
            config["vector_store"]["port"] = 6333  # default
            
        if os.getenv("QDRANT_COLLECTION_NAME"):
            config["vector_store"]["collection_name"] = os.getenv("QDRANT_COLLECTION_NAME")
        else:
            config["vector_store"]["collection_name"] = "query_templates_unified"  # default
        
        # OpenAI configuration (from .env)
        config.setdefault("embedding", {})
        if os.getenv("OPENAI_API_KEY"):
            config["embedding"]["api_key"] = os.getenv("OPENAI_API_KEY")
        if os.getenv("OPENAI_EMBEDDING_MODEL"):
            config["embedding"]["model"] = os.getenv("OPENAI_EMBEDDING_MODEL")
        else:
            config["embedding"]["model"] = "text-embedding-3-large"  # default
            
        # Logging configuration (from .env)
        if os.getenv("LOG_LEVEL"):
            config.setdefault("logging", {})["level"] = os.getenv("LOG_LEVEL")
        
        # Query Assistant specific overrides (if any)
        if os.getenv("QUERY_ASSISTANT_API_HOST"):
            config.setdefault("api_server", {})["host"] = os.getenv("QUERY_ASSISTANT_API_HOST")
        if os.getenv("QUERY_ASSISTANT_API_PORT"):
            config.setdefault("api_server", {})["port"] = int(os.getenv("QUERY_ASSISTANT_API_PORT"))
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation
        
        Args:
            key_path: Dot-separated path to configuration value (e.g., "database.sqlite.path")
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section
        
        Args:
            section: Top-level section name (e.g., "database", "vector_store")
        
        Returns:
            Configuration section as dictionary
        """
        return self._config.get(section, {})
    
    @property
    def database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        db_config = self.get_section("database")
        db_type = db_config.get("default_type", "sqlite")
        
        # For SQLite, path comes from env or default
        if db_type == "sqlite":
            return {
                "type": "sqlite",
                "path": db_config.get("path", "./data/iacsgraph.db")
            }
        
        # For other database types, would need additional config
        return {"type": db_type}
    
    @property
    def vector_store_config(self) -> Dict[str, Any]:
        """Get vector store configuration"""
        vs_config = self.get_section("vector_store")
        
        return {
            "provider": vs_config.get("provider", "qdrant"),
            "url": vs_config.get("url", "localhost"),
            "port": vs_config.get("port", 6333),
            "collection_name": vs_config.get("collection_name", "query_templates_unified"),
            "search": vs_config.get("search", {}),
            "cache": vs_config.get("cache", {})
        }
    
    @property
    def embedding_config(self) -> Dict[str, Any]:
        """Get embedding configuration"""
        emb_config = self.get_section("embedding")
        
        result = {
            "provider": emb_config.get("provider", "openai"),
            "model": emb_config.get("model", "text-embedding-3-large"),
            "dimension": emb_config.get("dimension", 3072),
            "batch_size": emb_config.get("batch_size", 100),
            "timeout": emb_config.get("timeout", 30),
            "max_retries": emb_config.get("max_retries", 3),
            "rate_limiting": emb_config.get("rate_limiting", {}),
            "api_key": emb_config.get("api_key")  # From env variable
        }
        
        return result
    
    @property
    def query_defaults(self) -> Dict[str, Any]:
        """Get default query parameters"""
        return self.get("query_processing.defaults", {})
    
    @property
    def api_server_config(self) -> Dict[str, Any]:
        """Get API server configuration"""
        return self.get_section("api_server")
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.get_section("logging")
    
    def reload(self):
        """Reload configuration from file"""
        self._config = self._load_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """Return full configuration as dictionary"""
        return self._config.copy()


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_path: str = None) -> Config:
    """Get configuration singleton instance
    
    Args:
        config_path: Path to configuration file (only used on first call)
    
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config():
    """Reload configuration from file"""
    global _config
    if _config is not None:
        _config.reload()