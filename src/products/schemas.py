from datetime import datetime
from decimal import Decimal
from typing import Annotated

from core.schemas import Base64Int, BaseDTO, UrlStr, _unset
from pydantic import AfterValidator, Field


def _check_datetime[T: datetime](value: T) -> T:
    assert value > datetime.now(
        value.tzinfo
    ), "Value should be greater than current datetime"
    return value


def _check_discount[T: int](value: T) -> T:
    assert 0 <= value <= 100, "Discount should be between 0 and 100"
    return value


def _check_query(value: str) -> str:
    stripped = value.strip()
    assert stripped
    return stripped


DateTimeAfterNow = Annotated[datetime, AfterValidator(_check_datetime)]
SearchQuery = Annotated[str, AfterValidator(_check_query)]
ProductDiscount = Annotated[int, AfterValidator(_check_discount)]


class CategoryDTO(BaseDTO):
    id: Base64Int = Field(gt=0)
    name: str = _unset
    url: str = _unset


class PlatformDTO(CategoryDTO): ...


class DeliveryMethodDTO(CategoryDTO): ...


class BaseProductDTO(BaseDTO):
    name: str = Field(min_length=3)
    description: str = Field(min_length=10)
    regular_price: Decimal = Field(ge=0)
    discount: ProductDiscount = 0
    image_url: UrlStr


class CreateProductDTO(BaseProductDTO):
    category: CategoryDTO
    platform: PlatformDTO
    delivery_method: DeliveryMethodDTO
    discount_valid_to: DateTimeAfterNow | None = None


class UpdateProductDTO(BaseDTO):
    name: str = Field(min_length=3, default=_unset)
    description: str = Field(min_length=10, default=_unset)
    regular_price: Decimal = Field(ge=0, default=_unset)
    category: CategoryDTO = _unset
    platform: PlatformDTO = _unset
    delivery_method: DeliveryMethodDTO = _unset
    image_url: UrlStr = _unset
    discount: ProductDiscount = _unset
    discount_valid_to: DateTimeAfterNow | None = _unset


class BaseShowProductDTO(BaseProductDTO):
    id: Base64Int
    discount_valid_to: datetime | None
    total_price: Decimal
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
