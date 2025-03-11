from sales.schemas import ExchangeRatesMappingDTO
from gateways.db import RedisClient
from sales.models import PriceUnit
from sales.schemas import SetExchangeRateDTO


class CurrencyConverter:
    def __init__(self, redis: RedisClient) -> None:
        self._db = redis
        self._key = "rub_exchange_rates"

    async def get_rub_exchange_rates(self) -> ExchangeRatesMappingDTO:
        res = await self._db.hgetall(self._key)
        return ExchangeRatesMappingDTO.model_validate(
            {"rub/" + curr.lower(): rate for curr, rate in res.items()}
        )

    async def set_rub_exchange_rate(self, dto: SetExchangeRateDTO):
        await self._db.hset(self._key, dto.to.lower(), dto.value)

    async def convert_to_rub(self, price: PriceUnit) -> PriceUnit:
        curr = price.currency_code.lower()
        exchange_rate = await self._db.hget(self._key, curr)
        if exchange_rate is None:
            raise ValueError("Exchange rate for currency %s wasn't found" % curr)
        converted = round(price * float(exchange_rate), 2)
        converted.currency_code = "RUB"
        return converted
