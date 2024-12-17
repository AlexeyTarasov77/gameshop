from datetime import datetime
from decimal import Decimal
from typing import Annotated

from core.schemas import Base64Int, BaseDTO
from pydantic import AfterValidator, AnyUrl, Field


def _check_datetime[T: datetime](value: T) -> T:
    assert value > datetime.now(), "Value should be greater than current datetime"
    return value


def _check_discount[T: int](value: T) -> T:
    assert 0 <= value <= 100, "Discount should be between 0 and 100"
    return value


DateTimeAfterNow = Annotated[datetime, AfterValidator(_check_datetime)]
ProductDiscount = Annotated[int, AfterValidator(_check_discount)]


class CategoryDTO(BaseDTO):
    id: Base64Int = Field(gt=0)
    name: str = None
    url: str = None


class PlatformDTO(CategoryDTO): ...


class DeliveryMethodDTO(CategoryDTO): ...


class BaseProductDTO(BaseDTO):
    name: str = Field(min_length=3)
    description: str = Field(min_length=10)
    regular_price: Decimal = Field(ge=0)
    discount: ProductDiscount = None
    image_url: AnyUrl


class CreateProductDTO(BaseProductDTO):
    category: CategoryDTO
    platform: PlatformDTO
    delivery_method: DeliveryMethodDTO
    discount_valid_to: DateTimeAfterNow | None = None


class UpdateProductDTO(BaseDTO):
    name: str = Field(min_length=3, default=None)
    description: str = Field(min_length=10, default=None)
    regular_price: Decimal = Field(ge=0, default=None)
    category: CategoryDTO = None
    platform: PlatformDTO = None
    delivery_method: DeliveryMethodDTO = None
    image_url: AnyUrl = None
    discount: ProductDiscount = None
    discount_valid_to: DateTimeAfterNow | None = None


class BaseShowProductDTO(BaseProductDTO):
    id: Base64Int
    discount_valid_to: datetime | None
    created_at: datetime
    updated_at: datetime


class ShowProduct(BaseShowProductDTO):
    category_id: Base64Int
    platform_id: Base64Int
    delivery_method_id: Base64Int


class ShowProductWithRelations(BaseShowProductDTO):
    category: CategoryDTO
    platform: PlatformDTO
    delivery_method: DeliveryMethodDTO
