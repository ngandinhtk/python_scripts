"""Logging configuration."""
import logging
import sys
from datetime import datetime


class StructuredLogger:
    """Structured logging wrapper."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
    
    def debug(self, msg: str, **kwargs):
        """Log debug message with context."""
        context = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.debug(f"{msg} {context}".strip())
    
    def info(self, msg: str, **kwargs):
        """Log info message with context."""
        context = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.info(f"{msg} {context}".strip())
    
    def error(self, msg: str, **kwargs):
        """Log error message with context."""
        context = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.error(f"{msg} {context}".strip())
    
    def warning(self, msg: str, **kwargs):
        """Log warning message with context."""
        context = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.warning(f"{msg} {context}".strip())


logger = StructuredLogger(__name__)


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
