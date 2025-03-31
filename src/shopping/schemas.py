from pydantic import Field
from core.schemas import Base64Int, BaseDTO, ProductRegion
from products.models import EMPTY_REGION


class ItemInCartDTO(BaseDTO):
    product_id: Base64Int
    region: ProductRegion = EMPTY_REGION
    quantity: int | None = Field(gt=0, default=1)
