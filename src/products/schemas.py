from datetime import datetime
from decimal import Decimal
from typing import Annotated

from core.schemas import Base64Int, BaseDTO, ImgUrl, ParseJson, UploadImage, unset
from pydantic import AfterValidator, Field


def _check_datetime[T: datetime](value: T) -> T:
    assert value > datetime.now(
        value.tzinfo
    ), "Value should be greater than current datetime"
    return value


def _check_discount[T: int](value: T) -> T:
    assert 0 <= value <= 100, "Discount should be between 0 and 100"
    return value


DateTimeAfterNow = Annotated[datetime, AfterValidator(_check_datetime)]
ProductDiscount = Annotated[int, AfterValidator(_check_discount)]


class CategoryDTO(BaseDTO):
    id: Base64Int = Field(gt=0)
    name: str = unset
    url: str = unset


class PlatformDTO(CategoryDTO): ...


class DeliveryMethodDTO(CategoryDTO): ...


class BaseProductDTO(BaseDTO):
    name: str = Field(min_length=3)
    description: str = Field(min_length=10)
    regular_price: Decimal = Field(ge=0)
    discount: ProductDiscount = 0


class CreateProductDTO(BaseProductDTO):
    category: Annotated[CategoryDTO, ParseJson]
    platform: Annotated[PlatformDTO, ParseJson]
    delivery_method: Annotated[DeliveryMethodDTO, ParseJson]
    discount_valid_to: DateTimeAfterNow | None = None
    image: UploadImage = unset


class UpdateProductDTO(BaseDTO):
    name: str = Field(min_length=3, default=unset)
    description: str = Field(min_length=10, default=unset)
    regular_price: Decimal = Field(ge=0, default=unset)
    category: CategoryDTO = unset
    platform: PlatformDTO = unset
    delivery_method: DeliveryMethodDTO = unset
    image: UploadImage = unset
    discount: ProductDiscount = unset
    discount_valid_to: DateTimeAfterNow | None = unset


class BaseShowProductDTO(BaseProductDTO):
    id: Base64Int
    discount_valid_to: datetime | None
    total_price: Decimal
    total_discount: int
    created_at: datetime
    updated_at: datetime
    image_url: ImgUrl


class ShowProduct(BaseShowProductDTO):
    category_id: Base64Int
    platform_id: Base64Int
    delivery_method_id: Base64Int


class ShowProductWithRelations(BaseShowProductDTO):
    category: CategoryDTO
    platform: PlatformDTO
    delivery_method: DeliveryMethodDTO
