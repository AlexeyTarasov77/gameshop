import typing as t
import math
from fastapi import Query, Depends
from pydantic import Field, computed_field, model_validator
from core.schemas import BaseModel


class PaginationParams(BaseModel):
    page_size: int = Field(default=10, gt=0, lt=100)
    page_num: int = Field(default=1, gt=0)

    def calc_offset(self):
        return self.page_size * (self.page_num - 1)


async def get_pagination_params(
    params: t.Annotated[PaginationParams, Query()],
) -> PaginationParams:
    return PaginationParams(**params.model_dump())


PaginationDep = t.Annotated[PaginationParams, Depends(get_pagination_params)]


class PaginatedResponse(PaginationParams):
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
