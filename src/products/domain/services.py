from abc import ABC, abstractmethod
import asyncio
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
from gateways.currency_converter.schemas import PriceUnitDTO
from gateways.db.exceptions import (
    AlreadyExistsError,
    NotFoundError,
    OperationRestrictedByRefError,
)
from products.domain.interfaces import (
    CurrencyConverterI,
    SaveGameRes,
    LoadPsnWithXboxRes,
)

from orders.domain.interfaces import SteamAPIClientI
from products.models import (
    Product,
    ProductCategory,
    ProductDeliveryMethod,
    ProductPlatform,
    RegionalPrice,
    SalesCategories,
    XboxParseRegions,
)
from products.schemas import (
    CategoriesListDTO,
    CreateProductDTO,
    DeliveryMethodsListDTO,
    ListProductsFilterDTO,
    PlatformsListDTO,
    PsnGameParsedDTO,
    XboxGameParsedDTO,
    ShowProduct,
    ShowProductExtended,
    UpdatePricesDTO,
    UpdatePricesResDTO,
    UpdateProductDTO,
)


class AbstractPriceCalculator(ABC):
    def __post_init__(self): ...

    def __init__(self, price: PriceUnitDTO):
        self._price = price.value

    @abstractmethod
    def calc_for_region(self, region_code: str, *args, **kwargs) -> Decimal: ...

    def _add_percent(self, percent: int) -> Decimal:
        return self._price + self._price / 100 * percent


class XboxPriceCalculator(AbstractPriceCalculator):
    def __init__(self, price: PriceUnitDTO):
        assert price.currency_code.lower() == "usd", "Expected price with usd currency"
        super().__init__(price)

    def _calc_for_usa(self, with_gp: bool) -> Decimal:
        calculated = self._price * Decimal(0.75)
        if with_gp:
            calculated += 1
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

    def calc_for_region(self, region_code: str, *args, **kwargs) -> Decimal:
        match region_code.lower():
            case XboxParseRegions.US:
                return self._calc_for_usa(*args, **kwargs)
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

    async def _save_games_by_platform(
        self, products: Sequence[XboxGameParsedDTO | PsnGameParsedDTO]
    ) -> list[SaveGameRes]:
        """Returns list of ids of INSERTED (not updated) products"""
        res: list[SaveGameRes] = []
        platform = (
            ProductPlatform.XBOX
            if isinstance(products[0], XboxGameParsedDTO)
            else ProductPlatform.PSN
        )
        async with self._uow() as uow:
            for item in products:
                recalculated_prices: list[RegionalPrice] = []
                for region, price in item.prices.items():
                    if isinstance(item, XboxGameParsedDTO):
                        # if src currency != usd - convert it because all computations are done in dollars
                        if price.currency_code.lower() != "usd":
                            price = await self._currency_converter.convert_price(
                                price, "usd"
                            )
                        price.value = XboxPriceCalculator(price).calc_for_region(
                            region, with_gp=item.with_gp
                        )
                    price_in_rub = await self._currency_converter.convert_price(price)
                    recalculated_prices.append(
                        RegionalPrice(
                            base_price=price_in_rub.value,
                            region_code=region,
                            original_curr=price.currency_code,
                        )
                    )
                if platform == ProductPlatform.XBOX:
                    delivery_method = ProductDeliveryMethod.KEY
                    save_func = uow.products_repo.save_on_conflict_update_discount
                else:
                    delivery_method = ProductDeliveryMethod.ACCOUNT_PURCHASE
                    save_func = uow.products_repo.save_ignore_conflict

                product = Product(
                    **item.model_dump(exclude={"prices", "orig_url"}),
                    prices=recalculated_prices,
                    category=ProductCategory.GAMES,
                    delivery_method=delivery_method,
                    platform=platform,
                )
                inserted_id = await save_func(product)
                if inserted_id is not None:
                    res.append(SaveGameRes(inserted_id=inserted_id, url=item.orig_url))
        return res

    async def load_new_sales(
        self,
        psn_products: Sequence[PsnGameParsedDTO],
        xbox_product: Sequence[XboxGameParsedDTO],
    ):
        psn_res, xbox_res = await asyncio.gather(
            self._save_games_by_platform(psn_products),
            self._save_games_by_platform(xbox_product),
        )
        return LoadPsnWithXboxRes(psn_res, xbox_res)

    async def update_prices(self, dto: UpdatePricesDTO) -> UpdatePricesResDTO:
        async with self._uow as uow:
            products_ids_for_update = await uow.products_repo.fetch_ids_for_platforms(
                dto.for_platforms,
            )
            updated_count = await uow.products_prices_repo.add_percent_for_products(
                products_ids_for_update, dto.percent
            )
        return UpdatePricesResDTO(updated_count=updated_count)

    async def create_product(self, dto: CreateProductDTO) -> ShowProduct:
        base_price = dto.discounted_price / (100 - dto.discount) * 100
        original_curr = None
        if dto.platform in [ProductPlatform.XBOX, ProductPlatform.PSN]:
            original_curr = "usd"
        try:
            async with self._uow as uow:
                product = await uow.products_repo.create_with_price(
                    dto, base_price, original_curr
                )
        except AlreadyExistsError as e:
            raise EntityAlreadyExistsError(
                self.entity_name,
                **dto.model_dump(include=set(Product.unique_fields)),
            ) from e
        return ShowProduct.model_validate(product)

    async def list_products(
        self,
        dto: ListProductsFilterDTO,
        pagination_params: PaginationParams,
    ) -> PaginationResT[ShowProductExtended]:
        async with self._uow as uow:
            (
                products,
                total_records,
            ) = await uow.products_repo.filter_paginated_list(
                dto,
                pagination_params,
            )
        return [
            ShowProductExtended.model_validate(product) for product in products
        ], total_records

    async def get_product(self, product_id: int) -> ShowProductExtended:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.get_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
        return ShowProductExtended.model_validate(product)

    async def platforms_list(self) -> PlatformsListDTO:
        return PlatformsListDTO(platforms=list(ProductPlatform))

    async def categories_list(self) -> CategoriesListDTO:
        return CategoriesListDTO(
            categories=list(ProductCategory) + list(SalesCategories)
        )

    async def delivery_methods_list(self) -> DeliveryMethodsListDTO:
        return DeliveryMethodsListDTO(delivery_methods=list(ProductDeliveryMethod))

    async def update_product(
        self, product_id: int, dto: UpdateProductDTO
    ) -> ShowProduct:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.update_by_id_with_image(
                    product_id, dto, cast(str | None, dto.image)
                )
                if dto.base_price is not None:
                    await uow.products_prices_repo.update_for_product(
                        product.id, dto.base_price
                    )
        except AlreadyExistsError:
            raise EntityAlreadyExistsError(
                self.entity_name,
                **dto.model_dump(include=set(Product.unique_fields), exclude_none=True),
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
        self._logger.info(
            "Updating prices according to new rate for %s. Rate: %.2f",
            dto.from_ + "/" + dto.to,
            dto.new_rate,
        )
        # update existing prices with new rate (only that which was converted from updated rate)
        async with self._uow as uow:
            await uow.products_prices_repo.update_all_with_rate(
                dto.from_, dto.new_rate, old_rate
            )

    async def get_exchange_rates(self) -> ExchangeRatesMappingDTO:
        return await self._currency_converter.get_exchange_rates()
