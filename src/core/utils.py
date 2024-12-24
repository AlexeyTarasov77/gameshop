import abc
from collections.abc import Mapping
from functools import partial
import logging
import typing as t


def filename_split(orig_filename: str) -> tuple[str, list[str]]:
    """Splits filename to name and extensions"""
    filename_splitted = orig_filename.split(".")
    filename_i = 1 if orig_filename.startswith(".") else 0
    filename = filename_splitted[filename_i]
    if orig_filename.startswith("."):
        filename = "." + filename
    extensions = filename_splitted[filename_i + 1 :]
    return filename, extensions


class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs) -> t.Self:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


class AbstractExceptionMapper[K: Exception, V: Exception](abc.ABC):
    EXCEPTION_MAPPING: Mapping[type[K], type[V]]

    @classmethod
    @abc.abstractmethod
    def get_default_exc(cls) -> type[V]: ...

    @classmethod
    def map(cls, exc: K | V) -> type[V] | partial[V]:
        exc_class = type(exc)
        if exc_class in cls.EXCEPTION_MAPPING.values():
            return t.cast(type[V], exc_class)
        mapped_exc_class = cls.EXCEPTION_MAPPING.get(t.cast(type[K], exc_class))
        if not mapped_exc_class:
            logging.warning("Not mapped exception: %s", exc_class)
            return cls.get_default_exc()
        return mapped_exc_class

    @classmethod
    def map_and_raise(cls, exc: K) -> t.NoReturn:
        mapped = cls.map(exc)
        raise mapped()
