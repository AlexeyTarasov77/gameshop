from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic_extra_types.currency_code import Currency
from typing import Any, Annotated

from core.schemas import (
    Base64Int,
    BaseDTO,
    DateTimeAfterNow,
    ExchangeRate,
    ImgUrl,
    ProductDiscount,
    UploadImage,
)
from pydantic import (
    Field,
    PlainSerializer,
    RootModel,
    computed_field,
)

from products.models import (
    ProductCategory,
    ProductDeliveryMethod,
    PsnParseRegions,
    XboxParseRegions,
    ProductPlatform,
)

ExchangeRatesMappingDTO = RootModel[dict[ExchangeRate, float]]


class SetExchangeRateDTO(BaseDTO):
    from_: Currency = Field(alias="from")
    to: Currency = Field(default=Currency("RUB"))
    value: float


class _BaseContentTypeDTO[T: Enum](BaseDTO):
    name: T = Field(serialization_alias="id")

    @computed_field
    def label(self) -> str:
        print(type(self.name.value))
        return getattr(self.name.value, "label", "")

    @computed_field
    def url(self) -> str:
        return self.name.name.replace("_", "").lower()


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
    category: ProductCategory
    platform: ProductPlatform
    delivery_method: ProductDeliveryMethod
    discounted_price: Decimal
    deal_until: DateTimeAfterNow | None = None
    image: UploadImage


def _base_field_ser(v: Enum) -> dict[str, Any]:
    name = v.value.label
    url = v.name.replace("_", "-").lower()
    return {"name": name, "url": url, "id": v.value}


ProductPlatformField = Annotated[ProductPlatform, PlainSerializer(_base_field_ser)]
ProductCategoryField = Annotated[ProductCategory, PlainSerializer(_base_field_ser)]
ProductDeliveryMethodField = Annotated[
    ProductDeliveryMethod, PlainSerializer(_base_field_ser)
]


class UpdateProductDTO(BaseDTO):
    name: str | None = Field(min_length=3, default=None)
    in_stock: bool | None = None
    description: str | None = Field(min_length=10, default=None)
    regular_price: Decimal | None = Field(ge=0, default=None)
    category: ProductCategory | None = None
    platform: ProductPlatform | None = None
    delivery_method: ProductDeliveryMethod | None = None
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
    delivery_method: ProductDeliveryMethodField


class PriceUnitDTO(BaseDTO):
    currency_code: Currency
    value: Decimal


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
    prices: dict[XboxParseRegions | PsnParseRegions, PriceUnitDTO]


class ListProductsFilterDTO(BaseDTO):
    query: str | None = None
    discounted: bool | None = None
    in_stock: bool | None = None
    category: ProductCategory | None = None
    region: str | None = None


class RegionalWithDiscountedPriceDTO(RegionalPriceDTO):
    discounted_price: Decimal


class ShowProductWithPrices(ShowProduct):
    prices: list[RegionalWithDiscountedPriceDTO]


class ProductInCartDTO(ShowProductWithPrices):
    quantity: int = Field(gt=0)
