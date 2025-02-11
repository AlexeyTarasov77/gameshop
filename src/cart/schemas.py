from pydantic import Field
from core.schemas import Base64Int, BaseDTO


class AddToCartDTO(BaseDTO):
    product_id: Base64Int
    quantity: int | None = Field(gt=0, default=1)
