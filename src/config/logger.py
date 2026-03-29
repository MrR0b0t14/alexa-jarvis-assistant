"""Logging configuration."""

import logging

LOG_FORMAT = "[%(levelname)s] %(name)s: %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger for the given module name.

    Args:
        name: The module name, typically ``__name__``.

    Returns:
        A configured ``logging.Logger`` instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger
