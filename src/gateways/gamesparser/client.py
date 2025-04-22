from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from logging import Logger
import time
import asyncio

from gamesparser.models import PsnParsedItem, XboxParsedItem

from core.uow import AbstractUnitOfWork
from products.domain.interfaces import SaveGameRes
from products.domain.services import ProductsService

from httpx import AsyncClient
from gamesparser import ParsedItem, PsnParser, XboxParser

from products.models import (
    PsnParseRegions,
    XboxParseRegions,
)
from products.schemas import PsnGameParsedDTO, XboxGameParsedDTO

type PsnUpdateRows = list[tuple[int, str, datetime | None]]
type XboxUpdateRows = list[tuple[int, str]]


class SalesParser:
    def __init__(
        self,
        logger: Logger,
        client: AsyncClient,
        products_service: ProductsService,
        uow: AbstractUnitOfWork,
    ):
        self._logger = logger
        self._client = client
        self._service = products_service
        self._uow = uow
        self._xbox_parser = XboxParser(self._client)
        self._psn_parser = PsnParser(self._client)

    def _parsed_to_dict(self, parsed: ParsedItem):
        return {
            **asdict(parsed),
            "image_url": parsed.preview_img_url,
        }

    def _parsed_xbox_to_dto(self, parsed_product: XboxParsedItem) -> XboxGameParsedDTO:
        return XboxGameParsedDTO.model_validate(
            {"with_gp": parsed_product.with_sub, **self._parsed_to_dict(parsed_product)}
        )

    def _parsed_psn_to_dto(self, product: PsnParsedItem) -> PsnGameParsedDTO:
        return PsnGameParsedDTO.model_validate(self._parsed_to_dict(product))

    async def _save_parsed(
        self, psn_sales: Sequence[PsnParsedItem], xbox_sales: Sequence[XboxParsedItem]
    ):
        psn_dtos: list[PsnGameParsedDTO] = [
            self._parsed_psn_to_dto(product) for product in psn_sales
        ]
        xbox_dtos: list[XboxGameParsedDTO] = [
            self._parsed_xbox_to_dto(product) for product in xbox_sales
        ]
        return await self._service.load_new_sales(psn_dtos, xbox_dtos)

    async def parse_and_save_all(self, parse_limit: int | None = None):
        limit_per_parser = parse_limit // 2 if parse_limit else None
        self._logger.info(
            "Start parsing%ssales...",
            (f" up to {parse_limit} " if parse_limit is not None else " "),
        )
        t1 = time.perf_counter()
        psn_regions = [el.value for el in PsnParseRegions]
        psn_sales, xbox_sales = await asyncio.gather(
            self._psn_parser.parse(psn_regions, limit_per_parser),
            self._xbox_parser.parse([XboxParseRegions.US], limit_per_parser),
        )
        self._logger.info(
            "%s sales succesfully parsed, which took: %s seconds",
            len(psn_sales) + len(xbox_sales),
            round(time.perf_counter() - t1, 1),
        )
        self._logger.info("Loading sales to db...")
        res = await self._save_parsed(psn_sales, xbox_sales)
        self._logger.info("Sales succesfully loaded")
        return res

    async def update_psn_details(
        self, products_urls: Sequence[SaveGameRes], timeout: int | None = None
    ):
        self._logger.info(
            "Start updating psn details for %d products", len(products_urls)
        )
        if not len(products_urls):
            self._logger.info("Nothing to update. Exiting...")
            return
        t1 = time.perf_counter()
        rows: PsnUpdateRows = []
        for obj in products_urls:
            data = await self._psn_parser.parse_item_details(obj.url)
            if data is None:
                self._logger.warning(
                    "Failed to parse details for psn product with inserted_id: %d. Left unchaged",
                    obj.inserted_id,
                )
                continue
            rows.append((obj.inserted_id, data.description, data.deal_until))
            if timeout:
                await asyncio.sleep(timeout)
        self._logger.info("PSN Parsed %d rows for update. Updating...", len(rows))
        async with self._uow as uow:
            await uow.products_repo.update_psn_details(rows)
        self._logger.info(
            "PSN update completed. Which took: %.2f seconds", time.perf_counter() - t1
        )

    async def update_xbox_details(self, products_urls: Sequence[SaveGameRes]):
        self._logger.info(
            "Start updating xbox details for %d products", len(products_urls)
        )
        if not len(products_urls):
            self._logger.info("Nothing to update. Exiting...")
            return
        t1 = time.perf_counter()
        rows: XboxUpdateRows = []
        for obj in products_urls:
            data = await self._xbox_parser.parse_item_details(obj.url)
            if data is None:
                self._logger.warning(
                    "Failed to parse details for xbox product with inserted_id: %d. Left unchaged",
                    obj.inserted_id,
                )
                continue
            rows.append((obj.inserted_id, data.description))
        self._logger.info("XBOX Parsed %d rows for update. Updating...", len(rows))
        async with self._uow as uow:
            await uow.products_repo.update_xbox_details(rows)
        self._logger.info(
            "XBOX update completed. Which took: %.2f seconds", time.perf_counter() - t1
        )
