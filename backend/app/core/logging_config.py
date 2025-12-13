import logging
from typing import Optional


def configure_logging(log_level: int = logging.INFO) -> None:
    """Configure root logging for the backend."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger instance."""
    return logging.getLogger(name if name else __name__)
