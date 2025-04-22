from decimal import Decimal
from .schemas import PriceUnitDTO, ExchangeRatesMappingDTO, SetExchangeRateDTO
from gateways.db import RedisClient


class CurrencyConverter:
    def __init__(self, redis: RedisClient) -> None:
        self._db = redis
        self._name = "exchange_rates"

    def _build_key(self, rate_from: str, rate_to: str) -> str:
        return f"{rate_from}/{rate_to}".lower()

    async def get_exchange_rates(self) -> ExchangeRatesMappingDTO:
        res = await self._db.hgetall(self._name)
        return ExchangeRatesMappingDTO.model_validate(res)

    async def get_rate_for(
        self, rate_from: str, rate_to: str = "rub"
    ) -> Decimal | None:
        key = self._build_key(rate_from, rate_to)
        res = await self._db.hget(self._name, key)
        return Decimal(res) if res else None

    async def set_exchange_rate(self, dto: SetExchangeRateDTO):
        await self._db.hset(
            self._name, self._build_key(dto.from_, dto.to), str(dto.new_rate)
        )

    async def convert_price(
        self, price: PriceUnitDTO, to_curr: str = "rub"
    ) -> PriceUnitDTO:
        if price.currency_code.lower() == to_curr.lower():
            return price
        exchange_rate = await self.get_rate_for(price.currency_code, to_curr)
        if exchange_rate is None:
            reversed_rate = await self.get_rate_for(to_curr, price.currency_code)
            if reversed_rate is None:
                raise ValueError(
                    "Exchange rate for exchanging %s to %s wasn't found"
                    % (price.currency_code, to_curr)
                )
            return PriceUnitDTO.model_validate(
                {"value": price.value / reversed_rate, "currency_code": to_curr}
            )
        return PriceUnitDTO.model_validate(
            {"value": price.value * exchange_rate, "currency_code": to_curr}
        )
