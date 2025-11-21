import logging
import os
import sys
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically the service name)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Set log level from environment or default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)
    
    # Create formatter with structured format
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger

