from datetime import datetime
from uuid import UUID
from pydantic_extra_types.currency_code import Currency
from pydantic import Field, RootModel
from core.schemas import BaseDTO, ExchangeRate, ProductDiscount, RoundedFloat
from sales.models import ProductOnSaleCategory


class SalesFilterDTO(BaseDTO):
    category: ProductOnSaleCategory | None = None
    region: str | None = None


class PriceUnitDTO(BaseDTO):
    currency_code: Currency
    value: RoundedFloat


class RegionalPriceDTO(BaseDTO):
    region: str
    base_price: PriceUnitDTO
    discounted_price: PriceUnitDTO


ExchangeRatesMappingDTO = RootModel[dict[ExchangeRate, float]]


class SetExchangeRateDTO(BaseDTO):
    from_: Currency = Field(default=Currency("RUB"), alias="from")
    to: Currency
    value: float


class ProductOnSaleDTO(BaseDTO):
    id: UUID
    name: str
    discount: ProductDiscount
    image_url: str
    with_gp: bool | None = None
    deal_until: datetime | None = None
    prices: list[RegionalPriceDTO]  # type: ignore
    category: ProductOnSaleCategory
