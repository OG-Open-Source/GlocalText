import logging
import sys
import time
from glocaltext import __version__


def setup_logger(level=logging.INFO):
    """
    Set up the logger.
    """
    logger = logging.getLogger("glocaltext")
    logger.setLevel(level)

    # Create a handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Create a formatter and add it to the handler
    log_format = (
        f"%(asctime)s | GlocalText - {__version__} - %(levelname)s - %(message)s"
    )
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%dT%H:%M:%SZ")
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)

    # Add the handler to the logger
    if not logger.handlers:
        logger.addHandler(handler)

    return logger
