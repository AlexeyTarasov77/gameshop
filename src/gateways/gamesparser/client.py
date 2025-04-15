from collections.abc import Sequence
from dataclasses import asdict
from logging import Logger
import time
import asyncio
import sys

from products.schemas import SalesDTO

from products.domain.services import ProductsService
from products.models import ProductPlatform

from httpx import AsyncClient
from gamesparser import ParsedItem, PsnParser, XboxParser

from products.models import (
    PsnParseRegions,
    XboxParseRegions,
)


class SalesParser:
    def __init__(
        self, logger: Logger, client: AsyncClient, products_service: ProductsService
    ):
        self._logger = logger
        self._client = client
        self._service = products_service

    def _parsed_to_dto(
        self, product: ParsedItem, platform: ProductPlatform
    ) -> SalesDTO:
        return SalesDTO.model_validate(
            {
                **asdict(product),
                "platform": platform,
                "prices": {k: v.base_price for k, v in product.prices.items()},
            }
        )

    async def _load_parsed(
        self, psn_sales: Sequence[ParsedItem], xbox_sales: Sequence[ParsedItem]
    ):
        sales: list[SalesDTO] = []
        for product in psn_sales:
            sales.append(self._parsed_to_dto(product, ProductPlatform.PSN))
        for product in xbox_sales:
            sales.append(self._parsed_to_dto(product, ProductPlatform.XBOX))
        await self._service.load_new_sales(sales)

    async def parse_and_save(self):
        try:
            limit_per_platform = int(sys.argv[1]) // 2
        except Exception:
            limit_per_platform = None
        self._logger.info(
            "Start parsing%ssales...",
            (
                f" up to {limit_per_platform * 2} "
                if limit_per_platform is not None
                else " "
            ),
        )
        psn_parser = PsnParser(
            [el.value for el in PsnParseRegions], self._client, limit_per_platform
        )
        xbox_parser = XboxParser(
            [XboxParseRegions.US], self._client, limit_per_platform
        )
        t1 = time.perf_counter()
        psn_sales, xbox_sales = await asyncio.gather(
            psn_parser.parse(), xbox_parser.parse()
        )
        self._logger.info(
            "%s sales succesfully parsed, which took: %s seconds",
            len(psn_sales) + len(xbox_sales),
            round(time.perf_counter() - t1, 1),
        )
        self._logger.info("Loading sales to db...")
        await self._load_parsed(psn_sales, xbox_sales)
        self._logger.info("Sales succesfully loaded")
