from datetime import datetime
from decimal import Decimal

from core.schemas import BaseDTO
from pydantic import FileUrl, field_validator


class CreateProductDTO(BaseDTO):
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
        from products.models import Product

        if value not in Product.DELIVERY_METHODS_CHOICES:
            raise ValueError(
                f"{value} is not available delivery method. Choices are: {Product.DELIVERY_METHODS_CHOICES}"
            )
        return value


class ShowProduct(CreateProductDTO):
    id: int
    created_at: datetime
    updated_at: datetime
