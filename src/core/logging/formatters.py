from collections.abc import Mapping
import logging
import json

from core.utils import CustomJSONEncoder


class Color:
    _reset_code: str = "\x1b[0m"

    def __init__(self, code: str):
        self.code = code

    def colorize(self, s: str) -> str:
        return self.code + s + self._reset_code


class Colors:
    GREY = Color("\x1b[0;37m")
    GREEN = Color("\x1b[1;32m")
    YELLOW = Color("\x1b[1;33m")
    RED = Color("\x1b[1;31m")
    PURPLE = Color("\x1b[1;35m")
    BLUE = Color("\x1b[1;34m")
    LIGHT_BLUE = Color("\x1b[1;36m")
    BLINK_RED = Color("\x1b[5m\x1b[1;31m")


class ColorizedFormatter(logging.Formatter):
    COLORS_MAPPING = {
        logging.DEBUG: Colors.GREY,
        logging.INFO: Colors.LIGHT_BLUE,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BLINK_RED,
    }

    def __init__(self) -> None:
        super().__init__(
            "%(asctime)s %(name)s (%(filename)s:%(lineno)d) %(levelname)s - %(message)s %(attrs)s"
        )

    def format(self, record: logging.LogRecord) -> str:
        fmt = self.COLORS_MAPPING[record.levelno].colorize(str(self._fmt))
        formatter = logging.Formatter(fmt)
        attrs: Mapping = getattr(record, "attrs")
        record.attrs = ", ".join(f"{key}={value}" for key, value in attrs.items())
        return formatter.format(record)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        res = {
            "severity": record.levelname,
            "resource": f"{record.pathname}:{record.lineno}",
            "attributes": getattr(record, "attrs"),
            "timestamp": self.formatTime(record),
            "body": record.msg,
        }
        return json.dumps(res, cls=CustomJSONEncoder)
