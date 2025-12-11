import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure structured logging that respects debug mode."""
    settings = get_settings()
    level = logging.DEBUG if settings.DEBUG else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )

    logger = logging.getLogger()
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.debug("logging configured", extra={"env": settings.ENVIRONMENT})
