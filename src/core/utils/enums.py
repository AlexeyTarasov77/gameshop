from enum import StrEnum, Enum
from typing import Any, Self


class CIEnum(StrEnum):
    """Adds support for caseinsensitive member lookup.
    Note that member name should be equal to it's value to work as expected"""

    @classmethod
    def _missing_(cls, value: Any) -> Self | None:
        return (isinstance(value, str) and cls.__members__.get(value.upper())) or None


class _labeledID(int):
    def __new__(cls, value: int, *args, **kwargs):
        if value <= 0:
            raise ValueError("id should be > 0")
        return super().__new__(cls, value)

    def __init__(self, _, label: str) -> None:
        super().__init__()
        self.label = label

    def __str__(self):
        return self.label


class LabeledEnum(Enum):
    def __new__(cls, value: str):
        cls._next_id = getattr(cls, "_next_id", 0) + 1
        obj = object.__new__(cls)
        obj._value_ = _labeledID(cls._next_id, value)
        return obj

    @classmethod
    def _missing_(cls, value: Any):
        try:
            if not isinstance(value, str):
                raise ValueError()
            # case-insensitive lookup in members first, then try to convert to int and find in values
            found = cls.__members__.get(value.upper()) or (
                int(value) in [member.value for member in cls.__members__.values()]
                and cls(int(value))
            )
            if not found:
                return None
            return found
        except ValueError:
            # value is not str or failed to convert to integer
            return None
