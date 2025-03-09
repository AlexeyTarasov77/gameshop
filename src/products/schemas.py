from datetime import datetime
from decimal import Decimal
from typing import Annotated

from core.schemas import (
    Base64Int,
    Base64IntOptionalIDParam,
    BaseDTO,
    DateTimeAfterNow,
    ImgUrl,
    ParseJson,
    ProductDiscount,
    UploadImage,
)
from pydantic import Field


class CategoryDTO(BaseDTO):
    id: Base64Int = Field(gt=0)
    name: str | None = None
    url: str | None = None


class ProductFromAPIDTO(BaseDTO):
    id: Base64Int
    name: str
    description: str
    price_rub: str
    image_url: str


class PlatformDTO(CategoryDTO): ...


class DeliveryMethodDTO(CategoryDTO): ...


class BaseProductDTO(BaseDTO):
    name: str = Field(min_length=3)
    description: str = Field(min_length=10)
    regular_price: Decimal = Field(ge=0)
    discount: ProductDiscount


class CreateProductDTO(BaseProductDTO):
    category: Annotated[CategoryDTO, ParseJson]
    platform: Annotated[PlatformDTO, ParseJson]
    delivery_method: Annotated[DeliveryMethodDTO, ParseJson]
    discount_valid_to: DateTimeAfterNow | None = None
    image: UploadImage


class UpdateProductDTO(BaseDTO):
    name: str | None = Field(min_length=3, default=None)
    in_stock: bool | None = None
    description: str | None = Field(min_length=10, default=None)
    regular_price: Decimal | None = Field(ge=0, default=None)
    category: Annotated[CategoryDTO | None, ParseJson] = None
    platform: Annotated[PlatformDTO | None, ParseJson] = None
    delivery_method: Annotated[DeliveryMethodDTO | None, ParseJson] = None
    image: UploadImage | None = None
    discount: ProductDiscount | None = None
    discount_valid_to: DateTimeAfterNow | None = None


class BaseShowProductDTO(BaseProductDTO):
    id: Base64Int
    discount_valid_to: datetime | None
    total_price: Decimal
    total_discount: int
    created_at: datetime
    updated_at: datetime
    image_url: ImgUrl
    in_stock: bool


class ListProductsFilterDTO(BaseDTO):
    query: str | None = None
    category_id: Base64IntOptionalIDParam = None
    discounted: bool | None = None
    in_stock: bool | None = None


class ShowProduct(BaseShowProductDTO):
    category_id: Base64Int
    platform_id: Base64Int
    delivery_method_id: Base64Int


class ShowProductWithRelations(BaseShowProductDTO):
    category: CategoryDTO
    platform: PlatformDTO
    delivery_method: DeliveryMethodDTO


class ProductInCartDTO(ShowProductWithRelations):
    quantity: int = Field(gt=0)
