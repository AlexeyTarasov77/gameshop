from datetime import datetime
from decimal import Decimal
from typing import Annotated

from core.schemas import BaseDTO
from pydantic import AfterValidator, AnyUrl, Field


def _check_datetime[T: datetime](value: T) -> T:
    assert value > datetime.now(), "Value should be greater than current datetime"
    return value


def _check_delivery_method[T: str | None](value: T) -> T:
    if value:
        from products.models import Product

        assert value in Product.DELIVERY_METHODS_CHOICES, f"""{value} is not available delivery method.
                Choices are: {Product.DELIVERY_METHODS_CHOICES}"""
    return value


def _check_discount[T: int](value: T) -> T:
    assert 0 <= value <= 100, "Discount should be between 0 and 100"
    return value


DateTimeAfterNow = Annotated[datetime, AfterValidator(_check_datetime)]
ProductDeliveryMethod = Annotated[str, AfterValidator(_check_delivery_method)]
ProductDiscount = Annotated[int, AfterValidator(_check_discount)]


class CategoryDTO(BaseDTO):
    id: int = Field(gt=0)
    name: str


class PlatformDTO(CategoryDTO): ...


class BaseProductDTO(BaseDTO):
    name: str = Field(min_length=3)
    description: str = Field(min_length=10)
    regular_price: Decimal = Field(ge=0)
    delivery_method: ProductDeliveryMethod
    discount: ProductDiscount = None
    image_url: AnyUrl


class CreateProductDTO(BaseProductDTO):
    category: CategoryDTO
    platform: PlatformDTO
    discount_valid_to: DateTimeAfterNow | None = None


class UpdateProductDTO(BaseDTO):
    name: str = Field(min_length=3, default=None)
    description: str = Field(min_length=10, default=None)
    regular_price: Decimal = Field(ge=0, default=None)
    category: CategoryDTO = None
    platform: PlatformDTO = None
    delivery_method: ProductDeliveryMethod = None
    image_url: AnyUrl = None
    discount: ProductDiscount = None
    discount_valid_to: DateTimeAfterNow | None = None


class BaseShowProductDTO(BaseProductDTO):
    id: int
    discount_valid_to: datetime | None
    created_at: datetime
    updated_at: datetime


class ShowProduct(BaseShowProductDTO):
    category_id: int
    platform_id: int


class ShowProductWithRelations(BaseShowProductDTO):
    category: CategoryDTO
    platform: PlatformDTO
