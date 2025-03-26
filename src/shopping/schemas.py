from typing import Annotated, Literal
from pydantic import BeforeValidator, Field
from pydantic_extra_types.country import CountryAlpha2
from core.schemas import Base64Int, BaseDTO

ProductRegion = Annotated[
    CountryAlpha2 | Literal[""],
    BeforeValidator(lambda s: s.strip() if isinstance(s, str) else s),
]


class ItemInCartDTO(BaseDTO):
    product_id: Base64Int
    region: ProductRegion = ""
    quantity: int | None = Field(gt=0, default=1)
