from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from logging import Logger
from typing import cast
from core.api.pagination import PaginationResT
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
from gateways.db import RedisClient
from products.domain.interfaces import (
    CommandExecutorI,
    CurrencyConverterI,
    ParsedUrlsMapping,
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
    BaseParsedGameDTO,
    CategoriesListDTO,
    CreateProductDTO,
    DeliveryMethodsListDTO,
    ListProductsParamsDTO,
    PlatformsListDTO,
    SalesUpdateDateDTO,
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

    def _add_percent(self, n: Decimal, percent: int) -> Decimal:
        return n + n / 100 * percent


class XboxPriceCalculator(AbstractPriceCalculator):
    def __init__(self, price: PriceUnitDTO):
        assert price.currency_code.lower() == "usd", "Expected price with usd currency"
        super().__init__(price)

    def _calc_for_us(self, with_gp: bool) -> Decimal:
        calculated = self._price * Decimal("0.73")
        calculated = calculated.quantize(Decimal(".001"))
        if with_gp:
            calculated += Decimal("1")

        if calculated <= Decimal("2.99"):
            calculated = self._add_percent(calculated, 120)
        elif calculated <= Decimal("4.99"):
            calculated = self._add_percent(calculated, 70)
        elif calculated <= Decimal("8.99"):
            calculated = self._add_percent(calculated, 40)
        elif calculated <= Decimal("12.99"):
            calculated = self._add_percent(calculated, 35)
        elif calculated <= Decimal("19.99"):
            calculated = self._add_percent(calculated, 28)
        elif calculated <= Decimal("29.99"):
            calculated = self._add_percent(calculated, 25)
        elif calculated <= Decimal("34.99"):
            calculated = self._add_percent(calculated, 23)
        elif calculated <= Decimal("39.99"):
            calculated = self._add_percent(calculated, 22)
        elif calculated <= Decimal("49.99"):
            calculated = self._add_percent(calculated, 21)
        else:
            calculated = self._add_percent(calculated, 20)

        return calculated

    def _calc_for_tr(self) -> Decimal:
        calculated = self._price
        if self._price <= Decimal("0.99"):
            calculated = self._add_percent(calculated, 200)
        elif self._price <= Decimal("1.99"):
            calculated = self._add_percent(calculated, 150)
        elif self._price <= Decimal("2.99"):
            calculated = self._add_percent(calculated, 80)
        elif self._price <= Decimal("4.99"):
            calculated = self._add_percent(calculated, 65)
        elif self._price <= Decimal("7.99"):
            calculated = self._add_percent(calculated, 55)
        elif self._price <= Decimal("9.99"):
            calculated = self._add_percent(calculated, 40)
        elif self._price <= Decimal("12.99"):
            calculated = self._add_percent(calculated, 35)
        elif self._price <= Decimal("15.99"):
            calculated = self._add_percent(calculated, 32)
        elif self._price <= Decimal("19.99"):
            calculated = self._add_percent(calculated, 28)
        elif self._price <= Decimal("24.99"):
            calculated = self._add_percent(calculated, 25)
        elif self._price <= Decimal("29.99"):
            calculated = self._add_percent(calculated, 24)
        else:
            calculated = self._add_percent(calculated, 21)
        return calculated

    def _calc_for_ar(self) -> Decimal:
        calculated = Decimal(0)
        addend: int | Decimal
        if self._price <= Decimal("0.2"):
            addend = Decimal("3.4")
        elif self._price <= Decimal("2.0"):
            addend = 5
        elif self._price <= Decimal("5.0"):
            addend = 7
        elif self._price <= Decimal("15.0"):
            addend = 10
        elif self._price <= Decimal("25.0"):
            addend = 12
        else:
            addend = 14
        if self._price > Decimal("0.2"):
            calculated = self._price * Decimal("1.7") / Decimal("1.1")
        return calculated + Decimal(addend)

    def calc_for_region(self, region_code: str, *args, **kwargs) -> Decimal:
        match region_code.lower():
            case XboxParseRegions.US:
                return self._calc_for_us(*args, **kwargs)
            case XboxParseRegions.TR:
                return self._calc_for_tr(*args, **kwargs)
            case XboxParseRegions.AR:
                return self._calc_for_ar(*args, **kwargs)
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
        cmd_executor: CommandExecutorI,
        redis_client: RedisClient,
    ) -> None:
        super().__init__(uow, logger)
        self._currency_converter = currency_converter
        self._steam_api = steam_api
        self._cmd_executor = cmd_executor
        self._redis_client = redis_client
        self._sales_last_update_date_key = (
            lambda platform: f"sales_last_updated:{platform}"
        )
        self._sales_update_state_key = (
            lambda platform: f"sales_update_started:{platform}"
        )

    async def save_parsed_products(
        self, products: Sequence[BaseParsedGameDTO]
    ) -> list[int]:
        """Returns list of ids of INSERTED (not updated) products"""
        res: list[int] = []
        async with self._uow() as uow:
            for item in products:
                platform = (
                    ProductPlatform.XBOX
                    if isinstance(item, XboxGameParsedDTO)
                    else ProductPlatform.PSN
                )
                recalculated_prices: list[RegionalPrice] = []
                for price_dto in item.prices:
                    if isinstance(item, XboxGameParsedDTO):
                        # if src currency != usd - convert it because all computations are done in dollars
                        if price_dto.currency_code.lower() != "usd":
                            self._logger.warning(
                                "Converting price from %s to usd. May cause miscalculation",
                                price_dto.currency_code,
                            )
                            price = await self._currency_converter.convert_price(
                                price_dto, "usd"
                            )
                            price_dto.value = price.value
                            price_dto.currency_code = price.currency_code
                        price_dto.value = XboxPriceCalculator(
                            price_dto
                        ).calc_for_region(price_dto.region, with_gp=item.with_gp)
                    price_in_rub = await self._currency_converter.convert_price(
                        price_dto
                    )
                    recalculated_prices.append(
                        RegionalPrice(
                            base_price=price_in_rub.value
                            * 100
                            / (100 - item.discount),  # compute base price
                            region_code=price_dto.region,
                            original_curr=price_dto.currency_code,
                        )
                    )
                if platform == ProductPlatform.XBOX:
                    delivery_method = ProductDeliveryMethod.KEY
                    save_func = uow.products_repo.save_on_conflict_update_discount
                else:
                    delivery_method = ProductDeliveryMethod.ACCOUNT_PURCHASE
                    save_func = uow.products_repo.save_ignore_conflict

                product = Product(
                    **item.model_dump(exclude={"prices"}),
                    prices=recalculated_prices,
                    category=ProductCategory.GAMES,
                    delivery_method=delivery_method,
                    platform=platform,
                )
                inserted_id = await save_func(product)
                if inserted_id is not None:
                    res.append(inserted_id)
        return res

    async def get_urls_mapping(self, by_ids: Sequence[int]) -> ParsedUrlsMapping:
        async with self._uow() as uow:
            products = await uow.products_repo.list_by_ids(by_ids)
        return {
            product.id: product.orig_url
            for product in products
            if product.orig_url is not None
        }

    async def update_prices(self, dto: UpdatePricesDTO) -> UpdatePricesResDTO:
        async with self._uow() as uow:
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
            async with self._uow() as uow:
                product = await uow.products_repo.create_with_price(
                    dto, base_price, original_curr
                )
        except AlreadyExistsError as e:
            raise EntityAlreadyExistsError(
                self.entity_name,
                **dto.model_dump(include=set(Product.unique_fields)),
            ) from e
        return ShowProduct.model_validate(product)

    async def list_all_products(self):
        async with self._uow() as uow:
            products = await uow.products_repo.get_all_in_stock()
        return [ShowProduct.model_validate(product) for product in products]

    async def list_products(
        self,
        dto: ListProductsParamsDTO,
    ) -> PaginationResT[ShowProductExtended]:
        async with self._uow() as uow:
            (
                products,
                total_records,
            ) = await uow.products_repo.filter_paginated_list(
                dto,
            )
        return [
            ShowProductExtended.model_validate(product) for product in products
        ], total_records

    async def get_product(self, product_id: int) -> ShowProductExtended:
        try:
            async with self._uow() as uow:
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
            async with self._uow() as uow:
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
            async with self._uow() as uow:
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
        # update existing prices with new rate (only that which were converted from original rate)
        async with self._uow() as uow:
            await uow.products_prices_repo.update_all_with_rate(
                dto.from_, dto.new_rate, old_rate
            )

    async def get_exchange_rates(self) -> ExchangeRatesMappingDTO:
        return await self._currency_converter.get_exchange_rates()

    async def check_sales_update_in_progress(
        self, platform: ProductPlatform | None = None
    ) -> bool:
        if await self._redis_client.get(self._sales_update_state_key(platform)):
            return True
        return False

    async def update_sales(self, platform: ProductPlatform | None = None):
        assert not await self.check_sales_update_in_progress(
            platform
        ), "Ensure that sales update is not started yet before calling this function"
        try:
            await self._redis_client.set(self._sales_update_state_key(platform), 1)
            cmd = "poetry run python scripts/sales/parse_and_save.py"
            if platform is not None:
                cmd += f" -p {str(platform.value)}"
            self._logger.info("Launching sales update on user demand")
            await self._cmd_executor.subprocess_exec(cmd)
            await self._redis_client.set(
                self._sales_last_update_date_key(platform), str(datetime.now(UTC))
            )
            await self._redis_client.delete(self._sales_update_state_key(platform))
            self._logger.info("Sales update completed")
        finally:
            await self._redis_client.delete(self._sales_update_state_key(platform))

    async def get_sales_update_date(
        self, platform: ProductPlatform | None = None
    ) -> SalesUpdateDateDTO:
        res = await self._redis_client.get(self._sales_last_update_date_key(platform))
        return SalesUpdateDateDTO(last_update_at=res)
