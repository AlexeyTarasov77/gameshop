from abc import ABC, abstractmethod
import logging
from .formatters import ColorizedFormatter, JsonFormatter


class AbstractLogger(ABC):
    @abstractmethod
    def debug(self, msg: str, **attrs): ...
    @abstractmethod
    def info(self, msg: str, **attrs): ...
    @abstractmethod
    def warning(self, msg: str, **attrs): ...
    @abstractmethod
    def error(self, msg: str, **attrs): ...
    @abstractmethod
    def exception(self, msg: str, **attrs): ...


class AppLogger(AbstractLogger):
    def __init__(self, debug: bool, error_log_path: str):
        logger = logging.Logger("GAMESHOP")
        logger.propagate = False
        logger.makeRecord = self.makeRecord
        logger.setLevel(logging.DEBUG if debug else logging.INFO)
        formatter = ColorizedFormatter()
        if not debug:
            formatter = JsonFormatter()
            file_handler = logging.FileHandler(error_log_path, "a")
            file_handler.setLevel(logging.WARNING)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        self._base_log = logger

    def makeRecord(
        self,
        name,
        level,
        fn,
        lno,
        msg,
        args,
        exc_info,
        func=None,
        extra=None,
        sinfo=None,
    ):
        rv = logging.LogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra is not None:
            rv.attrs = extra
        return rv

    def info(self, msg: str, **attrs) -> None:
        return self._base_log.info(msg, extra=attrs, stacklevel=2)

    def debug(self, msg: str, **attrs) -> None:
        return self._base_log.debug(msg, extra=attrs, stacklevel=2)

    def warning(self, msg: str, **attrs) -> None:
        return self._base_log.warning(msg, extra=attrs, stacklevel=2)

    def error(self, msg: str, **attrs) -> None:
        return self._base_log.error(msg, extra=attrs, stacklevel=2)

    def exception(self, msg: str, **attrs):
        return self._base_log.exception(msg, extra=attrs, stacklevel=2)


class StubLogger(AbstractLogger):
    """Logger stub for use in tests to avoid printing logging messages"""

    def debug(self, msg: str, **attrs): ...
    def info(self, msg: str, **attrs): ...
    def warning(self, msg: str, **attrs): ...
    def error(self, msg: str, **attrs): ...
    def exception(self, msg: str, **attrs): ...


stub_logger = StubLogger()
