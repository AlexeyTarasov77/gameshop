from datetime import datetime
from decimal import Decimal
from typing import Annotated

from core.schemas import BaseDTO, Image
from pydantic import AfterValidator, field_validator


def _check_datetime[T: datetime](value: T) -> T:
    assert value > datetime.now(), "Value should be greater than current datetime"
    return value


DateTimeAfterNow = Annotated[datetime, AfterValidator(_check_datetime)]


class BaseProductDTO(BaseDTO):
    name: str
    description: str
    regular_price: Decimal
    category_name: str
    platform_name: str
    delivery_method: str


class CreateProductDTO(BaseProductDTO):
    image: Image
    discount: int = 0
    discount_valid_to: DateTimeAfterNow | None = None

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
    image: Image = None
    discount: int = None
    discount_valid_to: DateTimeAfterNow | None = None


class ShowProduct(BaseProductDTO):
    id: int
    image_url: str
    discount: int
    discount_valid_to: datetime
    created_at: datetime
    updated_at: datetime
