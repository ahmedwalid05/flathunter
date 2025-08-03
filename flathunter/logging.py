"""Provides logger"""
import logging
import os
from pprint import pformat
from typing import Iterable


def _add_handler_once(target_logger: logging.Logger, handler: logging.Handler) -> None:
    """Attach handler if a same-class handler with same stream/filename isn't already attached."""
    for h in target_logger.handlers:
        if type(h) is type(handler):
            # For FileHandlers, compare filenames; for others, just class match is enough
            fn1 = getattr(h, "baseFilename", None)
            fn2 = getattr(handler, "baseFilename", None)
            if fn1 == fn2:
                return
            if fn1 is None and fn2 is None:
                return
    target_logger.addHandler(handler)


class LoggerHandler(logging.StreamHandler):
    """Formats logs and alters WebDriverManager's logs properties (stdout, colored)."""

    _CYELLOW = '\033[93m' if os.name == 'posix' else ''
    _CBLUE = '\033[94m' if os.name == 'posix' else ''
    _COFF = '\033[0m' if os.name == 'posix' else ''
    _FORMAT = '[' + _CBLUE + '%(asctime)s' + _COFF + \
              '|' + _CBLUE + '%(filename)-24s' + _COFF + \
              '|' + _CYELLOW + '%(levelname)-8s' + _COFF + \
              ']: %(message)s'
    _DATE_FORMAT = '%Y/%m/%d %H:%M:%S'

    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter(fmt=self._FORMAT, datefmt=self._DATE_FORMAT))

    def emit(self, record):
        # Log record came from webdriver-manager logger
        if record.name == "WDM":
            record.filename = "<WebDriverManager>"
            record.levelname = "DEBUG"
        super().emit(record)


class FileLoggerHandler(logging.FileHandler):
    """File logger without ANSI colors."""

    _FORMAT = '[%(asctime)s|%(filename)-24s|%(levelname)-8s]: %(message)s'
    _DATE_FORMAT = '%Y/%m/%d %H:%M:%S'

    def __init__(self, filename: str, mode: str = 'a'):
        # ensure directory exists
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        super().__init__(filename, mode=mode, encoding="utf-8", delay=False)
        self.setFormatter(logging.Formatter(fmt=self._FORMAT, datefmt=self._DATE_FORMAT))

    def emit(self, record):
        if record.name == "WDM":
            record.filename = "<WebDriverManager>"
            record.levelname = "DEBUG"
        super().emit(record)


def setup_wdm_logger(*handlers: Iterable[logging.Handler]):
    """Setup 'webdriver-manager' module's logger"""
    wdm_log = logging.getLogger('WDM')
    wdm_log.setLevel(logging.CRITICAL)  # muted by default
    wdm_log.propagate = False
    for h in handlers:
        _add_handler_once(wdm_log, h)
    return wdm_log


# ---------- Defaults ----------
LOG_FILE = os.environ.get("FLATHUNTER_LOG_FILE", "flathunter.log")

# Handlers
stdout_handler = LoggerHandler()
file_handler = FileLoggerHandler(LOG_FILE)

# Root logging config: send everything to both handlers at INFO by default
logging.basicConfig(level=logging.INFO, handlers=[stdout_handler, file_handler])

# App logger
logger = logging.getLogger('flathunt')

# "webdriver-manager" logger
wdm_logger = setup_wdm_logger(stdout_handler, file_handler)

# "requests" module logger
logging.getLogger("requests").setLevel(logging.WARNING)


def configure_logging(config, *, log_file: str | None = None):
    """Setup the logging classes based on verbose config flag and (optionally) a custom file path."""
    if log_file and os.path.abspath(log_file) != os.path.abspath(LOG_FILE):
        # Replace file handler with a new one pointing to the requested path
        new_file_handler = FileLoggerHandler(log_file)
        root_logger = logging.getLogger()
        _add_handler_once(root_logger, new_file_handler)
        _add_handler_once(wdm_logger, new_file_handler)

    if config.verbose_logging():
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)  # root
        wdm_logger.setLevel(logging.INFO)

    logger.debug("Settings from config: %s", pformat(config))
