from typing import Literal
from pydantic import Field
from pydantic_extra_types.country import CountryAlpha2
from core.schemas import Base64Int, BaseDTO


class ItemInCartDTO(BaseDTO):
    product_id: Base64Int
    region: CountryAlpha2 | Literal[""] = ""
    quantity: int | None = Field(gt=0, default=1)
