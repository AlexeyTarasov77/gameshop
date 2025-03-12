from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

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
from pydantic import Field, RootModel, computed_field

from products.models import (
    ProductCategory,
    ProductDeliveryMethod,
    PsnParseRegions,
    XboxParseRegions,
    ProductPlatform,
)

ExchangeRatesMappingDTO = RootModel[dict[ExchangeRate, float]]


class _BaseContentTypeDTO[T: Enum](BaseDTO):
    name: T

    @computed_field
    def id(self) -> UUID:
        return uuid4()

    @computed_field
    def url(self) -> str:
        enum_member = self.name
        return enum_member.name.replace("_", "").lower()


class RegionalPriceDTO(BaseDTO):
    base_price: Decimal
    region_code: str | None


class CategoryDTO(_BaseContentTypeDTO[ProductCategory]): ...


class PlatformDTO(_BaseContentTypeDTO[ProductPlatform]): ...


class DeliveryMethodDTO(_BaseContentTypeDTO[ProductDeliveryMethod]): ...


class BaseProductDTO(BaseDTO):
    name: str = Field(min_length=3)
    description: str
    discount: ProductDiscount


class CreateProductDTO(BaseProductDTO):
    category: Annotated[CategoryDTO, ParseJson]
    platform: Annotated[PlatformDTO, ParseJson]
    delivery_method: Annotated[DeliveryMethodDTO, ParseJson]
    prices: Annotated[list[RegionalPriceDTO], ParseJson]
    deal_until: DateTimeAfterNow | None = None
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
    deal_until: DateTimeAfterNow | None = None


class BaseShowProductDTO(BaseProductDTO):
    id: Base64Int
    deal_until: datetime | None
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
    discount: int
    image_url: str
    prices: dict[XboxParseRegions | PsnParseRegions, PriceUnitDTO]


class SteamItemDTO(ProductForLoadDTO):
    description: str


class SalesDTO(ProductForLoadDTO):
    platform: ProductPlatform
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


class RegionalWithDiscountedPriceDTO(RegionalPriceDTO):
    discounted_price: Decimal


class ShowProductWithRelations(BaseShowProductDTO):
    category: CategoryDTO
    platform: PlatformDTO
    delivery_method: DeliveryMethodDTO
    prices: list[RegionalWithDiscountedPriceDTO]


class ProductInCartDTO(ShowProductWithRelations):
    quantity: int = Field(gt=0)
