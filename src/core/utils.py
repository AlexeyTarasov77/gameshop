import abc
import logging
import typing as t


class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs) -> t.Self:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


class AbstractExceptionMapper[K: Exception, V: Exception](abc.ABC):
    EXCEPTION_MAPPING: dict[type[K], type[V]]

    @classmethod
    @abc.abstractmethod
    def get_default_exc(cls) -> type[Exception]: ...

    @classmethod
    def map(cls, exc: K) -> type[V]:
        exc_class = type(exc)
        if exc_class in cls.EXCEPTION_MAPPING.values():
            return exc_class
        mapped_exc_class = cls.EXCEPTION_MAPPING.get(exc_class)
        if not mapped_exc_class:
            logging.warning("Not mapped exception: %s", exc_class)
            return cls.get_default_exc()
        return mapped_exc_class

    @classmethod
    def map_and_raise(cls, exc: K) -> t.NoReturn:
        mapped = cls.map(exc)
        raise mapped()
