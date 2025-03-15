from abc import ABC, abstractmethod
from collections.abc import Sequence
from decimal import Decimal
from logging import Logger
from typing import cast
from core.pagination import PaginationParams, PaginationResT
from core.services.base import BaseService
from core.services.exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    EntityOperationRestrictedByRefError,
)
from core.uow import AbstractUnitOfWork
from gateways.currency_converter import ExchangeRatesMappingDTO, SetExchangeRateDTO
from gateways.db.exceptions import (
    AlreadyExistsError,
    NotFoundError,
    OperationRestrictedByRefError,
)
from products.domain.interfaces import CurrencyConverterI
from orders.domain.interfaces import SteamAPIClientI
from products.models import (
    Product,
    ProductCategory,
    ProductDeliveryMethod,
    ProductPlatform,
    RegionalPrice,
    XboxParseRegions,
)
from products.schemas import (
    CategoriesListDTO,
    CreateProductDTO,
    DeliveryMethodsListDTO,
    ListProductsFilterDTO,
    PlatformsListDTO,
    SalesDTO,
    ShowProduct,
    ShowProductWithPrices,
    SteamItemDTO,
    UpdateProductDTO,
)


class AbstractPriceCalculator(ABC):
    def __post_init__(self): ...

    def __init__(self, price: Decimal):
        self._price = price

    @abstractmethod
    def calc_for_region(self, region_code: str) -> Decimal: ...

    def _add_percent(self, percent: int) -> Decimal:
        return self._price + self._price / 100 * percent


class XboxPriceCalculator(AbstractPriceCalculator):
    def _calc_for_usa(self) -> Decimal:
        calculated = self._price * Decimal(0.75)
        if self._price <= 2.99:
            calculated = self._add_percent(70)
        elif self._price <= 4.99:
            calculated = self._add_percent(55)
        elif self._price <= 12.99:
            calculated = self._add_percent(35)
        elif self._price <= 29.99:
            calculated = self._add_percent(33)
        elif self._price <= 34.99:
            calculated = self._add_percent(31)
        elif self._price <= 39.99:
            calculated = self._add_percent(28)
        elif self._price <= 49.99:
            calculated = self._add_percent(25)
        elif self._price <= 54.99:
            calculated = self._add_percent(23)
        else:
            calculated = self._add_percent(20)
        return calculated

    def _calc_for_tr(self) -> Decimal:
        if self._price <= 0.99:
            calculated = self._add_percent(200)
        elif self._price <= 1.99:
            calculated = self._add_percent(150)
        elif self._price <= 2.99:
            calculated = self._add_percent(80)
        elif self._price <= 4.99:
            calculated = self._add_percent(65)
        elif self._price <= 7.99:
            calculated = self._add_percent(55)
        elif self._price <= 9.99:
            calculated = self._add_percent(40)
        elif self._price <= 12.99:
            calculated = self._add_percent(35)
        elif self._price <= 15.99:
            calculated = self._add_percent(32)
        elif self._price <= 19.99:
            calculated = self._add_percent(28)
        elif self._price <= 24.99:
            calculated = self._add_percent(25)
        elif self._price <= 29.99:
            calculated = self._add_percent(24)
        else:
            calculated = self._add_percent(21)
        return calculated

    def _calc_for_ar(self) -> Decimal:
        addend: float
        if self._price <= 0.2:
            addend = 3.4
        elif self._price <= 2.0:
            addend = 5
        elif self._price <= 5.0:
            addend = 7
        elif self._price <= 15.0:
            addend = 10
        elif self._price <= 25.0:
            addend = 12
        else:
            addend = 14
        calculated = 0
        if self._price > 0.2:
            calculated = self._price * Decimal(1.7) / Decimal(1.1)
        return calculated + Decimal(addend)

    def calc_for_region(self, region_code: str) -> Decimal:
        match region_code.lower():
            case XboxParseRegions.US:
                return self._calc_for_usa()
            case XboxParseRegions.TR:
                return self._calc_for_tr()
            case XboxParseRegions.AR:
                return self._calc_for_ar()
            case _:
                raise ValueError("Unsupported region: %s" % region_code)


class ProductsService(BaseService):
    entity_name = "Product"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        currency_converter: CurrencyConverterI,
        steam_api: SteamAPIClientI,
    ) -> None:
        super().__init__(uow, logger)
        self._currency_converter = currency_converter
        self._steam_api = steam_api

    async def load_new_sales(self, products: Sequence[SalesDTO]):
        products_for_save: list[Product] = []
        for item in products:
            calculated_prices: list[RegionalPrice] = []
            for region, price in item.prices.items():
                if item.platform == ProductPlatform.XBOX:
                    assert region in XboxParseRegions
                    new_value = XboxPriceCalculator(price.value).calc_for_region(region)
                    price.value = new_value
                price_in_rub = await self._currency_converter.convert_to_rub(price)
                calculated_prices.append(
                    RegionalPrice(
                        base_price=price_in_rub,
                        region_code=region,
                        converted_from_curr=price.currency_code,
                    )
                )
            if item.platform == ProductPlatform.XBOX:
                category = ProductCategory.XBOX_SALES
                delivery_method = (
                    ProductDeliveryMethod.ACCOUNT_PURCHASE
                    if XboxParseRegions.TR in item.prices
                    or XboxParseRegions.AR in item.prices
                    else ProductDeliveryMethod.KEY
                )
            else:
                category = ProductCategory.PSN_SALES
                delivery_method = ProductDeliveryMethod.KEY

            products_for_save.append(
                Product(
                    **item.model_dump(exclude={"prices"}),
                    prices=calculated_prices,
                    category=category,
                    delivery_method=delivery_method,
                )
            )
        async with self._uow as uow:
            await uow.products_repo.delete_for_categories(
                [ProductCategory.XBOX_SALES, ProductCategory.PSN_SALES]
            )
            await uow.products_repo.save_many(products_for_save)

    async def load_new_steam_items(self, items: Sequence[SteamItemDTO]):
        products_for_save = [
            Product(
                **item.model_dump(exclude={"price_rub"}),
                category=ProductCategory.STEAM_KEYS,
                delivery_method=ProductDeliveryMethod.KEY,
                platform=ProductPlatform.STEAM,
                prices=[RegionalPrice(base_price=item.price_rub)],
            )
            for item in items
        ]
        async with self._uow as uow:
            await uow.products_repo.delete_for_categories([ProductCategory.STEAM_KEYS])
            await uow.products_repo.save_many(products_for_save)

    async def create_product(self, dto: CreateProductDTO) -> ShowProduct:
        base_price = dto.discounted_price / (100 - dto.discount) * 100
        try:
            async with self._uow as uow:
                product = await uow.products_repo.create_with_dto(dto)
                await uow.prices_repo.add_price(product.id, base_price)
        except AlreadyExistsError as e:
            raise EntityAlreadyExistsError(
                self.entity_name,
                **dto.model_dump(include={"name", "category", "platform"}),
            ) from e
        return ShowProduct.model_validate(product)

    async def list_products(
        self,
        dto: ListProductsFilterDTO,
        pagination_params: PaginationParams,
    ) -> PaginationResT[ShowProductWithPrices]:
        async with self._uow as uow:
            (
                products,
                total_records,
            ) = await uow.products_repo.filter_paginated_list(
                dto,
                pagination_params,
            )
        dtos: list[ShowProductWithPrices] = []
        for product in products:
            [
                regional_price.calc_discounted_price(product.discount)
                for regional_price in product.prices
            ]
            dtos.append(ShowProductWithPrices.model_validate(product))
        return dtos, total_records

    async def get_product(self, product_id: int) -> ShowProductWithPrices:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.get_by_id(product_id)
                [
                    price.calc_discounted_price(product.discount)
                    for price in product.prices
                ]
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
        return ShowProductWithPrices.model_validate(product)

    async def platforms_list(self) -> PlatformsListDTO:
        return PlatformsListDTO(platforms=list(ProductPlatform))

    async def categories_list(self) -> CategoriesListDTO:
        return CategoriesListDTO(categories=list(ProductCategory))

    async def delivery_methods_list(self) -> DeliveryMethodsListDTO:
        return DeliveryMethodsListDTO(delivery_methods=list(ProductDeliveryMethod))

    async def update_product(
        self, product_id: int, dto: UpdateProductDTO
    ) -> ShowProduct:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.update_by_id(
                    product_id, dto, cast(str | None, dto.image)
                )
        except AlreadyExistsError:
            raise EntityAlreadyExistsError(
                self.entity_name,
                **dto.model_dump(
                    include={"name", "category", "platform"}, exclude_none=True
                ),
            )
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
        return ShowProduct.model_validate(product)

    async def delete_product(self, product_id: int) -> None:
        try:
            async with self._uow as uow:
                await uow.products_repo.delete_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
        except OperationRestrictedByRefError:
            raise EntityOperationRestrictedByRefError(self.entity_name)

    async def get_steam_exchange_rates(self) -> ExchangeRatesMappingDTO:
        return await self._steam_api.get_currency_rates()

    async def set_exchange_rate(self, dto: SetExchangeRateDTO) -> None:
        old_rate = await self._currency_converter.get_rate_for(dto.from_, dto.to)
        await self._currency_converter.set_exchange_rate(dto)
        if old_rate is None:
            return
        new_rate = dto.value
        # update existing prices with new rate (only that which was converted from updated rate)
        async with self._uow as uow:
            await uow.prices_repo.update_with_rate(dto.from_, new_rate, old_rate)

    async def get_exchange_rates(self) -> ExchangeRatesMappingDTO:
        return await self._currency_converter.get_exchange_rates()
