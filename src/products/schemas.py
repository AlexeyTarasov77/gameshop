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
    discount: int = 0
    discount_valid_to: datetime | None = None

    @field_validator("delivery_method")
    @classmethod
    def validate_delivery_method(cls, value):
        from products.models import Product

        if value not in Product.DELIVERY_METHODS_CHOICES:
            raise ValueError(
                f"""{value} is not available delivery method.
                Choices are: {Product.DELIVERY_METHODS_CHOICES}"""
            )
        return value


class UpdateProductDTO(BaseDTO):
    name: str = None
    description: str = None
    regular_price: Decimal = None
    category_name: str = None
    platform_name: str = None
    delivery_method: str = None
    image: UploadFile = None
    discount: int = None
    discount_valid_to: datetime | None = None


class ShowProduct(BaseProductDTO):
    id: int
    image_url: str
    discount: int
    discount_valid_to: datetime
    created_at: datetime
    updated_at: datetime
