"""Logger configuration for Query Assistant"""

import logging
import logging.handlers
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


def setup_file_logging(logger_name: str = "query_assistant", config_path: Optional[str] = None) -> logging.Logger:
    """Setup file logging based on settings.json configuration
    
    Args:
        logger_name: Name of the logger
        config_path: Path to settings.json (optional)
        
    Returns:
        Configured logger instance
    """
    # Get settings
    if config_path is None:
        config_path = Path(__file__).parent.parent / "settings.json"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)
    
    logging_config = settings.get("logging", {})
    
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging_config.get("level", "INFO"))
    
    # Clear existing handlers
    logger.handlers = []
    
    # Prevent propagation to parent loggers
    logger.propagate = False
    
    # Create formatter
    formatter = logging.Formatter(
        logging_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    # Console handler
    if logging_config.get("console", {}).get("enabled", True):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    file_config = logging_config.get("file", {})
    if file_config.get("enabled", True):
        # Create logs directory
        log_path = Path(__file__).parent.parent / file_config.get("path", "logs/query_assistant.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_path),
            maxBytes=file_config.get("max_size_mb", 100) * 1024 * 1024,  # Convert MB to bytes
            backupCount=file_config.get("backup_count", 5),
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Log initial message
        logger.info(f"🚀 File logging initialized at: {log_path}")
    
    return logger


def get_query_logger() -> logging.Logger:
    """Get or create query logger with file logging enabled"""
    logger_name = "query_assistant"
    logger = logging.getLogger(logger_name)
    
    # If logger has no handlers, set it up
    if not logger.handlers:
        setup_file_logging(logger_name)
    
    return logger


def log_query_execution(query: str, template_id: str, results: Dict[str, Any], execution_time: float):
    """Log query execution details in a structured format
    
    Args:
        query: User's natural language query
        template_id: Matched template ID
        results: Query results dictionary
        execution_time: Query execution time in seconds
    """
    logger = get_query_logger()
    
    log_entry = {
        "timestamp": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", (), None)),
        "event": "QUERY_EXECUTION",
        "user_query": query,
        "template_id": template_id,
        "results_count": len(results.get("results", [])),
        "execution_time": execution_time,
        "status": results.get("status", "success")
    }
    
    logger.info(f"📊 QUERY_LOG: {json.dumps(log_entry, ensure_ascii=False)}")
    
    return log_entry