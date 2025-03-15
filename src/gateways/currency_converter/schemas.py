from decimal import Decimal
from pydantic import Field, RootModel
from pydantic_extra_types.currency_code import Currency
from core.schemas import BaseDTO, ExchangeRate

ExchangeRatesMappingDTO = RootModel[dict[ExchangeRate, float]]


class PriceUnitDTO(BaseDTO):
    currency_code: Currency
    value: Decimal


class SetExchangeRateDTO(BaseDTO):
    from_: Currency = Field(alias="from")
    to: Currency = Field(default=Currency("RUB"))
    value: float
