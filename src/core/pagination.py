import typing as t
import math
from collections.abc import Sequence
from pydantic import Field, computed_field, model_validator
from core.schemas import BaseDTO, BaseModel


class PaginationParams(BaseModel):
    page_size: int = Field(default=10, gt=0, lt=100)
    page_num: int = Field(default=1, gt=0)

    def calc_offset(self):
        return self.page_size * (self.page_num - 1)


type PaginationResT[R] = tuple[Sequence[R], int]


class PaginatedResponse[T: BaseDTO](PaginationParams):
    objects: Sequence[T]
    total_records: int
    total_on_page: int
    first_page: int = 1

    @computed_field
    @property
    def last_page(self) -> int:
        return math.ceil(self.total_records / self.page_size)

    @model_validator(mode="after")
    def check_total_on_page_lt_page_size(self) -> t.Self:
        if self.total_on_page > self.page_size:
            raise ValueError("total_on_page should be <= page_size")
        return self
