from datetime import datetime
from decimal import Decimal

from core.schemas import BaseDTO
from fastapi import UploadFile
from pydantic import field_validator


class BaseProductDTO(BaseDTO):
    name: str
    description: str
    regular_price: Decimal
    category_name: str
    platform_name: str
    delivery_method: str


class CreateProductDTO(BaseProductDTO):
    image: UploadFile
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


class ShowProduct(BaseProductDTO):
    id: int
    image_url: str
    discount: int
    discount_valid_to: datetime
    created_at: datetime
    updated_at: datetime
