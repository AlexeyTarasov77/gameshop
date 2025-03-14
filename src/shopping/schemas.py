from pydantic import Field
from pydantic_extra_types.country import CountryAlpha2
from core.schemas import Base64Int, BaseDTO


class AddToCartDTO(BaseDTO):
    product_id: Base64Int
    region: CountryAlpha2 | None = None
    quantity: int | None = Field(gt=0, default=1)
