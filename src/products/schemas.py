from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic_extra_types.currency_code import Currency

from core.schemas import (
    Base64Int,
    Base64IntOptionalIDParam,
    BaseDTO,
    DateTimeAfterNow,
    ExchangeRate,
    ImgUrl,
    ParseJson,
    ProductDiscount,
    UploadImage,
)
from pydantic import Field, RootModel

from products.models import PsnParseRegions, XboxParseRegions, ProductPlatform

ExchangeRatesMappingDTO = RootModel[dict[ExchangeRate, float]]


class CategoryDTO(BaseDTO):
    id: Base64Int = Field(gt=0)
    name: str | None = None
    url: str | None = None


class RegionalPriceDTO(BaseDTO):
    id: Base64Int
    base_price: Decimal
    region_code: str | None


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
    description: str
    discount: ProductDiscount


class CreateProductDTO(BaseProductDTO):
    category: Annotated[CategoryDTO, ParseJson]
    platform: Annotated[PlatformDTO, ParseJson]
    delivery_method: Annotated[DeliveryMethodDTO, ParseJson]
    prices: Annotated[list[RegionalPriceDTO], ParseJson]
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
    total_discount: int
    created_at: datetime
    updated_at: datetime
    image_url: ImgUrl
    in_stock: bool


class PriceUnitDTO(BaseDTO):
    currency_code: Currency
    value: Decimal


class ProductForLoadDTO(BaseDTO):
    name: str
    platform: ProductPlatform
    discount: int
    prices: dict[XboxParseRegions | PsnParseRegions, PriceUnitDTO]
    image_url: str
    with_gp: bool | None = None
    deal_until: datetime | None = None


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
    prices: list[RegionalPriceDTO]


class ProductInCartDTO(ShowProductWithRelations):
    quantity: int = Field(gt=0)
