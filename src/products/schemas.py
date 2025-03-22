from datetime import datetime
from pydantic_extra_types.country import CountryAlpha2
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Any, Annotated

from core.schemas import (
    Base64Int,
    BaseDTO,
    DateTimeAfterNow,
    ImgUrl,
    ProductDiscount,
    RoundedPrice,
    UploadImage,
)
from pydantic import (
    Field,
    PlainSerializer,
)

from gateways.currency_converter import PriceUnitDTO
from products.models import (
    ProductCategory,
    ProductDeliveryMethod,
    PsnParseRegions,
    XboxParseRegions,
    ProductPlatform,
)


def _base_field_ser(v: Enum) -> dict[str, Any]:
    name = v.value.label
    url = v.name.replace("_", "-").lower()
    return {"name": name, "url": url, "id": v.value}


ProductPlatformField = Annotated[ProductPlatform, PlainSerializer(_base_field_ser)]
ProductCategoryField = Annotated[ProductCategory, PlainSerializer(_base_field_ser)]
ProductDeliveryMethodField = Annotated[
    ProductDeliveryMethod, PlainSerializer(_base_field_ser)
]


class RegionalPriceDTO(BaseDTO):
    base_price: RoundedPrice
    region_code: str | None


class CategoriesListDTO(BaseDTO):
    categories: list[ProductCategoryField]


class PlatformsListDTO(BaseDTO):
    platforms: list[ProductPlatformField]


class DeliveryMethodsListDTO(BaseDTO):
    delivery_methods: list[ProductDeliveryMethodField]


class BaseProductDTO(BaseDTO):
    name: str = Field(min_length=3)
    description: str
    discount: ProductDiscount


class CreateProductDTO(BaseProductDTO):
    category: ProductCategory
    platform: ProductPlatform
    discounted_price: Decimal
    deal_until: DateTimeAfterNow | None = None
    image: UploadImage


class UpdateProductDTO(BaseDTO):
    name: str | None = Field(min_length=3, default=None)
    in_stock: bool | None = None
    description: str | None = Field(min_length=10, default=None)
    regular_price: Decimal | None = Field(ge=0, default=None)
    category: ProductCategory | None = None
    platform: ProductPlatform | None = None
    image: UploadImage | None = None
    discount: ProductDiscount | None = None
    deal_until: DateTimeAfterNow | None = None


class ShowProduct(BaseProductDTO):
    id: Base64Int
    deal_until: datetime | None
    total_discount: int
    created_at: datetime
    updated_at: datetime
    image_url: ImgUrl
    in_stock: bool
    category: ProductCategoryField
    platform: ProductPlatformField
    delivery_methods: list[ProductDeliveryMethodField]


class ProductForLoadDTO(BaseDTO):
    name: str
    discount: int
    image_url: str


class SteamItemDTO(ProductForLoadDTO):
    description: str
    price_rub: Decimal


class SalesDTO(ProductForLoadDTO):
    platform: ProductPlatform
    with_gp: bool | None = None
    deal_until: datetime | None = None
    prices: dict[PsnParseRegions | XboxParseRegions, PriceUnitDTO]


class OrderByOption(StrEnum):
    ASC = "asc"
    DESC = "desc"


class ListProductsFilterDTO(BaseDTO):
    query: str | None = None
    discounted: bool | None = None
    in_stock: bool | None = None
    categories: list[ProductCategory] | None = None
    platforms: list[ProductPlatform] | None = None
    delivery_methods: list[ProductDeliveryMethod] | None = None
    regions: list[CountryAlpha2] | None = None
    price_ordering: OrderByOption | None = None


class RegionalWithDiscountedPriceDTO(RegionalPriceDTO):
    discounted_price: RoundedPrice


class ShowProductExtended(ShowProduct):
    prices: list[RegionalWithDiscountedPriceDTO]


class ProductInCartDTO(ShowProductExtended):
    quantity: int = Field(gt=0)
