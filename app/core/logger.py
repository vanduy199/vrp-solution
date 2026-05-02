import logging
import os
import sys

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("vrp")
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(_LOG_LEVEL)
    logger.propagate = False
    return logger


logger = _build_logger()
