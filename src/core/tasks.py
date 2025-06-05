import asyncio
from core.logging import AbstractLogger
from core.uow import AbstractUnitOfWork


class BackgroundJobs:
    def __init__(self, uow: AbstractUnitOfWork, logger: AbstractLogger):
        self._uow = uow
        self._logger = logger

    async def remove_products_from_sale(self, *, exit_after_update: bool = False):
        """Periodically updates products with expired discount.
        If exit_after_update is set to True - don't run an infinite loop
        and exit after first cleanup"""
        timeout_sec = 60 * 60 * 6  # 6 hours
        while True:
            async with self._uow() as uow:
                updated_count = await uow.products_repo.update_where_expired_discount(
                    deal_until=None, discount=0
                )
                self._logger.info("Products removed from sale", count=updated_count)
            if exit_after_update:
                return
            await asyncio.sleep(timeout_sec)

    def start_all(self):
        asyncio.create_task(self.remove_products_from_sale())
