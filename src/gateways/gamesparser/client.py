from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import datetime
from logging import Logger
import time
import asyncio
from typing import Literal, NamedTuple

from gamesparser.models import PsnParsedItem, XboxParsedItem
from gamesparser.psn import PsnItemDetails
from gamesparser.xbox import XboxItemDetails

from core.uow import AbstractUnitOfWork
from core.utils import measure_time_async
from products.domain.interfaces import ParsedUrlsMapping
from products.domain.services import ProductsService

from httpx import AsyncClient
from gamesparser import ParsedItem, PsnParser, XboxParser

from products.models import (
    ProductPlatform,
    PsnParseRegions,
    XboxParseRegions,
)
from products.schemas import PsnGameParsedDTO, XboxGameParsedDTO

type PsnUpdateRows = list[tuple[int, str, datetime | None]]
type XboxUpdateRows = list[tuple[int, str]]


class PsnRowForUpdate(NamedTuple):
    id: int
    description: str
    deal_until: datetime | None


class XboxRowForUpdate(NamedTuple):
    id: int
    description: str


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
            "prices": [
                {"region": region, **asdict(price)}
                for region, price in parsed.prices.items()
            ],
        }

    def _parsed_xbox_to_dto(self, parsed_product: XboxParsedItem) -> XboxGameParsedDTO:
        return XboxGameParsedDTO.model_validate(
            {"with_gp": parsed_product.with_sub, **self._parsed_to_dict(parsed_product)}
        )

    def _parsed_psn_to_dto(self, product: PsnParsedItem) -> PsnGameParsedDTO:
        return PsnGameParsedDTO.model_validate(self._parsed_to_dict(product))

    @measure_time_async
    async def parse_and_save_xbox(self, parse_limit: int | None = None):
        xbox_sales = await self._xbox_parser.parse([XboxParseRegions.US], parse_limit)
        self._logger.info("Xbox sales parsed. Saving...")
        mapped_to_dto = [self._parsed_xbox_to_dto(product) for product in xbox_sales]
        res = await self._service.save_parsed_products(mapped_to_dto)
        return res

    @measure_time_async
    async def parse_and_save_psn(self, parse_limit: int | None = None):
        psn_sales = await self._psn_parser.parse(
            [el.value for el in PsnParseRegions], parse_limit
        )
        self._logger.info("Psn sales parsed. Saving...")
        mapped_to_dto = [self._parsed_psn_to_dto(product) for product in psn_sales]
        res = await self._service.save_parsed_products(mapped_to_dto)
        return res

    async def _update_parsed_details[T](
        self,
        products_urls: ParsedUrlsMapping,
        for_platform: Literal[ProductPlatform.XBOX, ProductPlatform.PSN],
        parse_func: Callable[[str], Awaitable[T | None]],
        row_extracter: Callable[[int, T], NamedTuple],
        *,
        timeout: int | None = None,
    ):
        self._logger.info(
            "Start updating %s details for %d products",
            str(for_platform.value),
            len(products_urls),
        )
        if not len(products_urls):
            self._logger.info("Nothing to update. Exiting...")
            return
        t1 = time.perf_counter()
        rows: list[NamedTuple] = []
        for id, url in products_urls.items():
            try:
                data = await parse_func(url)
            except Exception as e:
                self._logger.error(
                    "Error during parsing details for id: %d, url: %s. Error: %s",
                    id,
                    url,
                    e,
                )
                continue
            if data is None:
                self._logger.warning(
                    "Failed to parse details for id: %d. Left unchaged",
                    id,
                )
                continue
            rows.append(row_extracter(id, data))
            if timeout:
                await asyncio.sleep(timeout)
        self._logger.info(
            "%s Parsed %d rows for update. Updating...",
            str(for_platform.value),
            len(rows),
        )
        async with self._uow() as uow:
            await uow.products_repo.update_from_rows(rows)
        self._logger.info(
            "%s update completed. Which took: %.2f seconds",
            str(for_platform.value),
            time.perf_counter() - t1,
        )

    async def update_psn_details(
        self, products_urls: ParsedUrlsMapping, timeout: int | None = None
    ):
        def row_extracter(id: int, data: PsnItemDetails) -> PsnRowForUpdate:
            return PsnRowForUpdate(id, data.description, data.deal_until)

        await self._update_parsed_details(
            products_urls,
            ProductPlatform.PSN,
            self._psn_parser.parse_item_details,
            row_extracter,
            timeout=timeout,
        )

    async def update_xbox_details(self, products_urls: ParsedUrlsMapping):
        def row_extracter(id: int, data: XboxItemDetails) -> XboxRowForUpdate:
            return XboxRowForUpdate(id, data.description)

        await self._update_parsed_details(
            products_urls,
            ProductPlatform.XBOX,
            self._xbox_parser.parse_item_details,
            row_extracter,
        )
