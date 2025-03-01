from datetime import datetime
from decimal import Decimal
from typing import Annotated

from core.schemas import (
    Base64Int,
    Base64IntOptionalIDParam,
    BaseDTO,
    ImgUrl,
    ParseJson,
    UploadImage,
)
from pydantic import AfterValidator, Field

from products.models import ProductOnSale, ProductOnSaleCategory


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
    name: str | None = None
    url: str | None = None


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


class _ProductOnSalePrice(BaseDTO):
    currency_code: str
    value: float


class SalesFilterDTO(BaseDTO):
    category: ProductOnSaleCategory | None = None
    region: str | None = None


class ProductOnSaleDTO(BaseDTO):
    id: int
    name: str
    discount: int
    base_price: _ProductOnSalePrice
    discounted_price: _ProductOnSalePrice
    image_url: str
    region: str
    with_gp: bool | None = None
    deal_until: datetime | None = None
    category: ProductOnSaleCategory

    @classmethod
    def from_model(cls, product: ProductOnSale):
        return cls.model_validate(
            {
                **product.dump(),
                "base_price": _ProductOnSalePrice(
                    value=product.base_price, currency_code=product.base_price_currency
                ),
                "discounted_price": _ProductOnSalePrice(
                    value=product.discounted_price,
                    currency_code=product.discounted_price_currency,
                ),
            }
        )
