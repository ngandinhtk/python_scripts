"""Logging configuration."""
import logging
import sys
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None


class StructuredLogger:
    """Structured logging wrapper."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def debug(self, msg: str, **kwargs):
        """Log debug message with context."""
        if jsonlogger:
            self.logger.debug(msg, extra=kwargs)
        else:
            self._log_fallback(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        """Log info message with context."""
        if jsonlogger:
            self.logger.info(msg, extra=kwargs)
        else:
            self._log_fallback(logging.INFO, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        """Log error message with context."""
        if jsonlogger:
            self.logger.error(msg, extra=kwargs)
        else:
            self._log_fallback(logging.ERROR, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """Log warning message with context."""
        if jsonlogger:
            self.logger.warning(msg, extra=kwargs)
        else:
            self._log_fallback(logging.WARNING, msg, **kwargs)

    def _log_fallback(self, level, msg, **kwargs):
        """Fallback logging when jsonlogger is not available."""
        if kwargs:
            context = " ".join(f"{k}={v}" for k, v in kwargs.items())
            msg = f"{msg} {context}"
        self.logger.log(level, msg)


def setup_logging():
    """Setup logging configuration to output JSON."""
    # Remove all handlers associated with the root logger object to avoid duplicates.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    log_handler = logging.StreamHandler(sys.stdout)
    
    if jsonlogger:
        # The format string defines the root fields of the JSON log.
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        # Fallback formatter for standard text logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    log_handler.setFormatter(formatter)
    logging.root.addHandler(log_handler)
    logging.root.setLevel(logging.INFO)
