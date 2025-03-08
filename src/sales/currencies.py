from redis.asyncio import Redis
from sales.domain.interfaces import ExchangeRatesMapping
from sales.models import Currencies, PriceUnit
from sales.schemas import ExchangeRateDTO


class CurrencyConverter:
    def __init__(self, redis: Redis) -> None:
        self._db = redis
        self._key = "rub_exchange_rates"

    async def get_rub_exchange_rates(self) -> ExchangeRatesMapping:
        res: ExchangeRatesMapping = await self._db.hgetall(self._key)
        return res

    async def set_rub_exchange_rate(self, dto: ExchangeRateDTO):
        await self._db.hset(self._key, dto.rate_for, dto.value)

    async def convert_to_rub(self, price: PriceUnit) -> PriceUnit:
        curr = price.currency_code.lower()
        assert curr in Currencies, "Unknown currency: %s" % price.currency_code
        exchange_rate = await self._db.hget(self._key, curr)
        if exchange_rate is None:
            raise ValueError("Exchange rate for currency %s wasn't found" % curr)
        converted = round(price * float(exchange_rate), 2)
        converted.currency_code = Currencies.RUB
        return converted
