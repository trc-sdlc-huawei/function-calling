import logging
import sys
from datetime import datetime


def setup_logger(name: str = "app_logger", level=logging.INFO, log_to_console=True, log_to_file=None):
    """Set up and return a logger with the given name and level."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')

    if log_to_console:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    if log_to_file:
        fh = logging.FileHandler(log_to_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.propagate = False
    return logger


def log_info(logger, msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def log_warning(logger, msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def log_error(logger, msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def log_debug(logger, msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

def log_exception(logger, msg, *args, **kwargs):
    logger.exception(msg, *args, **kwargs)


def log_separator(logger, sep_char="=", length=80):
    logger.info(sep_char * length)


def log_event(logger, event_name, details=None):
    logger.info(f"EVENT: {event_name} | Details: {details if details else ''}")


def log_dict(logger, d, dict_name="Dict"):
    logger.info(f"{dict_name}: {d}")
