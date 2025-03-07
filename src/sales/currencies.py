from redis.asyncio import Redis
from sales.models import Currencies, PriceUnit


class CurrencyConverter:
    def __init__(self, redis: Redis) -> None:
        self._db = redis
        self._key = "rub_exchange_rates"

    async def convert_to_rub(self, price: PriceUnit) -> PriceUnit:
        src_currency = price.currency_code.lower()
        assert src_currency in Currencies, "Unknown currency: %s" % price.currency_code
        exchange_rate = await self._db.hget(self._key, src_currency)
        if exchange_rate is None:
            raise ValueError(
                "Exchange rate for currency %s wasn't found" % src_currency
            )
        converted = round(price * float(exchange_rate), 2)
        converted.currency_code = Currencies.RUB
        return converted
