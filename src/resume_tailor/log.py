import logging
import logging.handlers
from pathlib import Path

_LOG_PATH = Path("outputs/tailor.log")


def get_logger() -> logging.Logger:
    logger = logging.getLogger("resume_tailor")
    if logger.hasHandlers():
        return logger

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        _LOG_PATH, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
    )
    logger.addHandler(handler)
    return logger
