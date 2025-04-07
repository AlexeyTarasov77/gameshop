import asyncio
from logging import Logger
from core.uow import AbstractUnitOfWork


class BackgroundJobs:
    def __init__(self, uow: AbstractUnitOfWork, logger: Logger):
        self._uow = uow
        self._logger = logger

    async def _remove_products_from_sale(self):
        """Changes product category from *_SALES to GAMES if discount expired.
        After every change waits for specified time interval"""
        timeout_sec = 60 * 60 * 6  # 6 hours
        while True:
            async with self._uow as uow:
                updated_count = await uow.products_repo.update_with_expired_discount(
                    deal_until=None, discount=0
                )
                self._logger.info("%d products removed from sale", updated_count)
            await asyncio.sleep(timeout_sec)

    def run(self):
        asyncio.create_task(self._remove_products_from_sale())
