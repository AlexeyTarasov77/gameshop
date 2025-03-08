from datetime import datetime
from uuid import UUID

from core.schemas import BaseDTO, ProductDiscount, RoundedFloat
from sales.models import Currencies, ProductOnSaleCategory


class SalesFilterDTO(BaseDTO):
    category: ProductOnSaleCategory | None = None
    region: str | None = None


class PriceUnitDTO(BaseDTO):
    currency_code: Currencies
    value: RoundedFloat


class RegionalPriceDTO(BaseDTO):
    region: str
    base_price: PriceUnitDTO
    discounted_price: PriceUnitDTO


class ProductOnSaleDTO(BaseDTO):
    id: UUID
    name: str
    discount: ProductDiscount
    image_url: str
    with_gp: bool | None = None
    deal_until: datetime | None = None
    prices: list[RegionalPriceDTO]  # type: ignore
    category: ProductOnSaleCategory
