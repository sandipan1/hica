import logging
import os
import sys
from typing import Any, Dict

import structlog

os.environ["HICA_LOG_LEVEL"] = "DEBUG"
# Global registry for thread-specific loggers
_thread_loggers = {}


def configure_logging():
    """Configure the base logging setup for the 'hica' namespace."""
    log_level = os.getenv("HICA_LOG_LEVEL", "INFO").upper()
    log_level_int = getattr(logging, log_level, logging.INFO)

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Configure the 'hica' logger
    logger = logging.getLogger("hica")
    logger.setLevel(log_level_int)  # Set logger level based on HICA_LOG_LEVEL

    # Remove existing handlers to avoid duplicates (inspired by FastMCP)
    logger.handlers = []

    # Add stream handler for console output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("%(message)s"))
    stream_handler.setLevel(log_level_int)
    logger.addHandler(stream_handler)

    # Configure structlog
    structlog.configure_once(  # Prevent reconfiguration issues
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create structlog logger
    structlog_logger = structlog.get_logger("hica")
    return structlog_logger


def get_thread_logger(thread_id: str, metadata: Dict[str, Any] = None):
    """Get or create a logger for a specific thread with its own log file."""
    if thread_id in _thread_loggers:
        return _thread_loggers[thread_id]

    # Get the underlying standard library logger
    std_logger = logging.getLogger("hica")

    # Remove existing file handlers to avoid duplicates
    std_logger.handlers = [
        h for h in std_logger.handlers if not isinstance(h, logging.FileHandler)
    ]

    # Add file handler for this specific thread
    log_file = f"logs/thread_{thread_id}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    file_handler.setLevel(logging.DEBUG)  # Always DEBUG for file
    std_logger.addHandler(file_handler)

    # Get structlog logger and bind context
    structlog_logger = structlog.get_logger("hica")
    if metadata is None:
        metadata = {}
    structlog_logger = structlog_logger.bind(thread_id=thread_id, **metadata)

    # Store in registry
    _thread_loggers[thread_id] = structlog_logger
    return structlog_logger


# Initialize the base logger
logger = configure_logging()
