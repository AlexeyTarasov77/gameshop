from datetime import datetime
from pydantic_extra_types.country import CountryAlpha2
from decimal import Decimal
from typing import Any, Annotated

from core import schemas
import pydantic

from core.pagination import PaginationParams
from core.utils.enums import LabeledEnum
from gateways.currency_converter import PriceUnitDTO
from products import models


def _base_field_ser(v: LabeledEnum) -> dict[str, Any]:
    name = v.value.label
    url = v.name.replace("_", "-").lower()
    return {"name": name, "url": url, "id": v.value}


def _check_discount[T: int](value: T) -> T:
    assert 0 <= value <= 100, "Discount should be between 0 and 100"
    return value


ProductPlatformField = Annotated[
    models.ProductPlatform, pydantic.PlainSerializer(_base_field_ser)
]
ProductCategoryField = Annotated[
    models.ProductCategory, pydantic.PlainSerializer(_base_field_ser)
]
ProductDeliveryMethodField = Annotated[
    models.ProductDeliveryMethod, pydantic.PlainSerializer(_base_field_ser)
]
SalesCategoryField = Annotated[
    models.SalesCategories, pydantic.PlainSerializer(_base_field_ser)
]
ProductDiscount = Annotated[int, pydantic.AfterValidator(_check_discount)]


class RegionalPriceDTO(schemas.BaseDTO):
    base_price: schemas.RoundedDecimal
    region_code: schemas.ProductRegion


class CategoriesListDTO(schemas.BaseDTO):
    categories: list[ProductCategoryField | SalesCategoryField]


class PlatformsListDTO(schemas.BaseDTO):
    platforms: list[ProductPlatformField]


class DeliveryMethodsListDTO(schemas.BaseDTO):
    delivery_methods: list[ProductDeliveryMethodField]


class BaseProductDTO(schemas.BaseDTO):
    name: str = pydantic.Field(min_length=3)
    description: str
    discount: ProductDiscount


class CreateProductDTO(BaseProductDTO):
    category: models.ProductCategory
    platform: models.ProductPlatform
    delivery_method: models.ProductDeliveryMethod
    discounted_price: Decimal
    deal_until: pydantic.FutureDatetime | None = None
    image: schemas.UploadImage
    sub_id: int | None = None

    @pydantic.model_validator(mode="after")
    def check_fields(self):
        if (
            self.platform == models.ProductPlatform.STEAM
            and self.category == models.ProductCategory.GAMES
            and not self.sub_id
        ):
            raise ValueError(
                "For product with steam platform and 'games' category - sub_id must be supplied"
            )

        return self


class UpdateProductDTO(schemas.BaseDTO):
    name: str | None = pydantic.Field(min_length=3, default=None)
    in_stock: bool | None = None
    description: str | None = pydantic.Field(min_length=10, default=None)
    base_price: Decimal | None = pydantic.Field(ge=0, default=None)
    category: models.ProductCategory | None = None
    platform: models.ProductPlatform | None = None
    image: schemas.UploadImage | None = None
    discount: ProductDiscount | None = None
    deal_until: pydantic.FutureDatetime | None = None


class UpdatePricesDTO(schemas.BaseDTO):
    for_platforms: list[models.ProductPlatform]
    # percent can be > 0 to add or < 0 to subtract
    percent: int

    @pydantic.field_validator("percent")
    @classmethod
    def check_percent(cls, val: int) -> int:
        if val == 0:
            raise ValueError("percent can't be equal to 0")
        return val


class UpdatePricesResDTO(schemas.BaseDTO):
    updated_count: int


class ShowProduct(BaseProductDTO):
    id: schemas.Base64Int
    deal_until: datetime | None
    total_discount: int
    created_at: datetime
    updated_at: datetime
    image_url: schemas.ImgUrl
    in_stock: bool
    category: ProductCategoryField
    platform: ProductPlatformField
    delivery_method: ProductDeliveryMethodField


class ParsedPriceDTO(PriceUnitDTO):
    region: str


class BaseParsedGameDTO(schemas.BaseDTO):
    name: str
    discount: int
    image_url: str
    prices: list[ParsedPriceDTO]
    orig_url: str = pydantic.Field(validation_alias="url")


class SteamGameParsedDTO(BaseParsedGameDTO):
    description: str
    price_rub: Decimal


class XboxGameParsedDTO(BaseParsedGameDTO):
    with_gp: bool | None
    deal_until: datetime | None


class PsnGameParsedDTO(BaseParsedGameDTO): ...


class ListProductsParamsDTO(PaginationParams):
    query: str | None = None
    discounted: bool | None = None
    in_stock: bool | None = None
    categories: list[models.ProductCategory] | None = None
    platforms: list[models.ProductPlatform] | None = None
    delivery_methods: list[models.ProductDeliveryMethod] | None = None
    regions: list[CountryAlpha2] | None = None
    price_ordering: schemas.OrderByOption | None = None


class RegionalWithDiscountedPriceDTO(RegionalPriceDTO):
    discounted_price: schemas.RoundedDecimal


class ShowProductExtended(ShowProduct):
    prices: list[RegionalWithDiscountedPriceDTO]

    @pydantic.model_validator(mode="before")
    @classmethod
    def calc_discounted_prices(cls, obj):
        if not isinstance(obj, models.Product):
            return obj
        [price.calc_discounted_price(obj.discount) for price in obj.prices]
        return obj


class ProductInCartDTO(ShowProductExtended):
    quantity: int = pydantic.Field(gt=0)
