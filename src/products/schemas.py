from datetime import datetime
from decimal import Decimal

from products.models import PRODUCT_DELIVERY_METHODS
from pydantic import BaseModel, FileUrl, field_validator


class CreateProductDTO(BaseModel):
    name: str
    description: str
    regular_price: Decimal
    category_name: str
    platform_name: str
    image_url: FileUrl
    delivery_method: str
    discount: int | None
    discount_valid_to: datetime | None

    @field_validator("delivery_method")
    @classmethod
    def validate_delivery_method(cls, value):
        if value not in PRODUCT_DELIVERY_METHODS:
            raise ValueError(
                f"{value} is not available delivery method. Choices are: {PRODUCT_DELIVERY_METHODS}"
            )
        return value
