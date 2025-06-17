import logging
import os
import sys
from typing import Any, Dict

import structlog


def configure_logging():
    """Configure the base logging setup."""
    log_level = os.getenv("HICA_LOG_LEVEL", "INFO").upper()

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    structlog.configure(
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

    return structlog.get_logger("hica")


def get_thread_logger(thread_id: str, metadata: Dict[str, Any]):
    """Get a logger bound to a specific thread context with its own log file."""
    # Create a unique log file for this thread
    log_file = f"logs/thread_{thread_id}.log"

    # Get the underlying standard library logger
    std_logger = logging.getLogger("hica")

    # Add file handler for this specific thread
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    std_logger.addHandler(file_handler)

    # Get the structlog logger and bind context
    logger = structlog.get_logger("hica")
    return logger.bind(thread_id=thread_id, **metadata)


# Initialize the base logger
logger = configure_logging()
