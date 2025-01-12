import logging


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
            "%(asctime)s %(name)s (%(filename)s:%(lineno)d) %(levelname)s - %(message)s"
        )

    def format(self, record: logging.LogRecord) -> str:
        fmt = self.COLORS_MAPPING[record.levelno].colorize(str(self._fmt))
        formatter = logging.Formatter(fmt)
        return formatter.format(record)


def setup_logger(debug: bool, error_log_path: str) -> logging.Logger:
    logger = logging.getLogger("GAMESHOP")
    logger.propagate = False
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    simple_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    colorized_formatter = ColorizedFormatter()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(colorized_formatter)
    logger.addHandler(stream_handler)
    if not debug:
        file_handler = logging.FileHandler(error_log_path, "a")
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(simple_formatter)
        logger.addHandler(file_handler)
    return logger
