from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import replace
from logging import Logger
from uuid import UUID
from core.pagination import PaginationParams
from core.services.base import BaseService
from core.services.exceptions import EntityNotFoundError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError
from sales.domain.interfaces import (
    CurrencyConverterI,
    SalesRepositoryI,
    SteamAPIClientI,
)
from sales.models import (
    XboxParseRegions,
    PriceUnit,
    ProductOnSale,
    ProductOnSaleCategory,
)
from sales.schemas import (
    SetExchangeRateDTO,
    ProductOnSaleDTO,
    SalesFilterDTO,
    ExchangeRatesMappingDTO,
)


class AbstractPriceCalculator(ABC):
    def __post_init__(self): ...

    def __init__(self, price: PriceUnit):
        self._initial_price = price
        self.__post_init__()

    @abstractmethod
    def compute_for_region(self, region_code: str) -> PriceUnit: ...


class XboxPriceCalculator(AbstractPriceCalculator):
    def __post_init__(self):
        curr = self._initial_price.currency_code.lower()
        assert curr == "usd", f"Expected currency: usd, got: {curr}"

    def _compute_for_usa(self) -> PriceUnit:
        new_price = self._initial_price * 0.75
        if new_price <= 2.99:
            new_price.add_percent(70)
        elif new_price <= 4.99:
            new_price.add_percent(55)
        elif new_price <= 12.99:
            new_price.add_percent(35)
        elif new_price <= 29.99:
            new_price.add_percent(33)
        elif new_price <= 34.99:
            new_price.add_percent(31)
        elif new_price <= 39.99:
            new_price.add_percent(28)
        elif new_price <= 49.99:
            new_price.add_percent(25)
        elif new_price <= 54.99:
            new_price.add_percent(23)
        else:
            new_price.add_percent(20)
        return new_price

    def _compute_for_tr(self) -> PriceUnit:
        new_price = replace(self._initial_price)  # make an object copy
        if new_price <= 0.99:
            new_price.add_percent(200)
        elif new_price <= 1.99:
            new_price.add_percent(150)
        elif new_price <= 2.99:
            new_price.add_percent(80)
        elif new_price <= 4.99:
            new_price.add_percent(65)
        elif new_price <= 7.99:
            new_price.add_percent(55)
        elif new_price <= 9.99:
            new_price.add_percent(40)
        elif new_price <= 12.99:
            new_price.add_percent(35)
        elif new_price <= 15.99:
            new_price.add_percent(32)
        elif new_price <= 19.99:
            new_price.add_percent(28)
        elif new_price <= 24.99:
            new_price.add_percent(25)
        elif new_price <= 29.99:
            new_price.add_percent(24)
        else:
            new_price.add_percent(21)
        return new_price

    def _compute_for_ar(self) -> PriceUnit:
        addend: float
        if self._initial_price <= 0.2:
            addend = 3.4
        elif self._initial_price <= 2.0:
            addend = 5
        elif self._initial_price <= 5.0:
            addend = 7
        elif self._initial_price <= 15.0:
            addend = 10
        elif self._initial_price <= 25.0:
            addend = 12
        else:
            addend = 14
        new_price = self._initial_price
        if self._initial_price > 0.2:
            new_price = self._initial_price * 1.7 / 1.1
        return new_price + addend

    def compute_for_region(self, region_code: str) -> PriceUnit:
        match region_code.lower():
            case XboxParseRegions.US:
                return self._compute_for_usa()
            case XboxParseRegions.TR:
                return self._compute_for_tr()
            case XboxParseRegions.AR:
                return self._compute_for_ar()
            case _:
                raise ValueError("Unsupported region: %s" % region_code)


class SalesService(BaseService):
    entity_name = "Product on sale"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        sales_repo: SalesRepositoryI,
        currency_converter: CurrencyConverterI,
        steam_api: SteamAPIClientI,
    ) -> None:
        super().__init__(uow, logger)
        self._sales_repo = sales_repo
        self._currency_converter = currency_converter
        self._steam_api = steam_api

    async def load_new_sales(self, sales: Sequence[ProductOnSale]):
        for item in sales:
            calculator_cls: type[AbstractPriceCalculator] | None = (
                XboxPriceCalculator
                if item.category.lower() == ProductOnSaleCategory.XBOX
                else None
            )
            for regional_price in item.prices:
                new_price = regional_price.discounted_price
                if calculator_cls:
                    calculator = calculator_cls(regional_price.discounted_price)
                    new_price = calculator.compute_for_region(regional_price.region)
                converted_price = await self._currency_converter.convert_to_rub(
                    new_price
                )
                regional_price.discounted_price = converted_price
        await self._sales_repo.delete_all()
        await self._sales_repo.create_many(
            [ProductOnSaleDTO.model_validate(item) for item in sales]
        )

    async def get_steam_exchange_rates(self) -> ExchangeRatesMappingDTO:
        return await self._steam_api.get_currency_rates()

    async def set_exchange_rate(self, dto: SetExchangeRateDTO) -> None:
        await self._currency_converter.set_rub_exchange_rate(dto)

    async def get_exchange_rates(self) -> ExchangeRatesMappingDTO:
        return await self._currency_converter.get_rub_exchange_rates()

    async def get_product_on_sale(self, product_id: UUID) -> ProductOnSaleDTO:
        try:
            product = await self._sales_repo.get_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
        return ProductOnSaleDTO.model_validate(product)

    async def delete_product_on_sale(self, product_id: UUID) -> None:
        try:
            await self._sales_repo.delete_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def get_current_sales(
        self,
        dto: SalesFilterDTO,
        pagination_params: PaginationParams,
    ) -> tuple[Sequence[ProductOnSaleDTO], int]:
        (
            items,
            total_records,
        ) = await self._sales_repo.filter_paginated_list(
            dto,
            pagination_params,
        )
        return [ProductOnSaleDTO.model_validate(item) for item in items], total_records
