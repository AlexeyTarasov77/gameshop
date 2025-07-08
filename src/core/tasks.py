import asyncio
from logging import Logger
from core.uow import AbstractUnitOfWork


class BackgroundJobs:
    def __init__(self, uow: AbstractUnitOfWork, logger: Logger):
        self._uow = uow
        self._logger = logger

    async def delete_expired_sales(self):
        """Deletes only parsed products which have expired discount"""
        timeout_sec = 60 * 60 * 24  # once per day
        while True:
            async with self._uow() as uow:
                deleted_count = await uow.products_repo.delete_parsed_without_discount()
                self._logger.info("removed %d parsed products", deleted_count)
            await asyncio.sleep(timeout_sec)

    async def reset_expired_discount(self, *, exit_after_update: bool = False):
        """Periodically updates products with expired discount.
        If exit_after_update is set to True - don't run an infinite loop
        and exit after first cleanup"""
        timeout_sec = 60 * 60 * 6  # 6 hours
        while True:
            async with self._uow() as uow:
                updated_count = await uow.products_repo.update_where_expired_discount(
                    deal_until=None, discount=0
                )
                self._logger.info("reset discount for %d products", updated_count)
            if exit_after_update:
                return
            await asyncio.sleep(timeout_sec)

    def start_all(self):
        asyncio.create_task(self.reset_expired_discount())
        asyncio.create_task(self.delete_expired_sales())
