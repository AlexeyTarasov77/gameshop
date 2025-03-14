from decimal import Decimal
from products.schemas import PriceUnitDTO
from products.schemas import ExchangeRatesMappingDTO, SetExchangeRateDTO
from gateways.db import RedisClient


class CurrencyConverter:
    def __init__(self, redis: RedisClient) -> None:
        self._db = redis
        self._name = "exchange_rates"

    async def get_exchange_rates(self) -> ExchangeRatesMappingDTO:
        res = await self._db.hgetall(self._name)
        return ExchangeRatesMappingDTO.model_validate(res)

    def _build_key(self, rate_from: str, rate_to: str) -> str:
        return f"{rate_from}/{rate_to}".lower()

    async def set_exchange_rate(self, dto: SetExchangeRateDTO):
        await self._db.hset(self._name, self._build_key(dto.from_, dto.to), dto.value)

    async def convert_to_rub(self, price: PriceUnitDTO) -> Decimal:
        rate_from = price.currency_code.lower()
        exchange_rate = await self._db.hget(
            self._name, self._build_key(rate_from, "rub")
        )
        if exchange_rate is None:
            raise ValueError("Exchange rate for currency %s wasn't found" % rate_from)
        return price.value * Decimal(exchange_rate)
