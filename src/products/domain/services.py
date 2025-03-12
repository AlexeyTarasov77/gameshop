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
from gateways.db.exceptions import (
    AlreadyExistsError,
    NotFoundError,
    OperationRestrictedByRefError,
)
from products.domain.interfaces import SteamAPIClientI, CurrencyConverterI
from products.models import (
    Product,
    ProductCategory,
    ProductDeliveryMethod,
    ProductPlatform,
    RegionalPrice,
    XboxParseRegions,
)
from products.schemas import (
    CategoryDTO,
    ProductForLoadDTO,
    ProductFromAPIDTO,
    DeliveryMethodDTO,
    CreateProductDTO,
    ListProductsFilterDTO,
    PlatformDTO,
    ShowProduct,
    ShowProductWithRelations,
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
        steam_api: SteamAPIClientI,
        currency_converter: CurrencyConverterI,
    ) -> None:
        super().__init__(uow, logger)
        self._api_client = steam_api
        self._currency_converter = currency_converter

    async def load_new_sales(self, products: Sequence[ProductForLoadDTO]):
        products_for_save: list[Product] = []
        for item in products:
            calculated_prices: list[RegionalPrice] = []
            for region, price in item.prices.items():
                if item.platform.lower() == ProductPlatform.XBOX:
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

    async def create_product(self, dto: CreateProductDTO) -> ShowProduct:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.create_with_image(
                    dto, cast(str, dto.image)
                )
        except AlreadyExistsError as e:
            raise EntityAlreadyExistsError(
                self.entity_name,
                name=dto.name,
                category_id=dto.category.id,
                platform_id=dto.platform.id,
            ) from e
        return ShowProduct.model_validate(product)

    async def list_products(
        self,
        dto: ListProductsFilterDTO,
        pagination_params: PaginationParams,
    ) -> tuple[list[ShowProductWithRelations], int]:
        async with self._uow as uow:
            (
                products,
                total_records,
            ) = await uow.products_repo.filter_paginated_list(
                dto,
                pagination_params,
            )
        return [
            ShowProductWithRelations.model_validate(product) for product in products
        ], total_records

    async def list_products_from_api(
        self, pagination_params: PaginationParams
    ) -> PaginationResT[ProductFromAPIDTO]:
        return await self._api_client.get_paginated_products(pagination_params)

    async def get_product_from_api(self, product_id: int) -> ProductFromAPIDTO:
        try:
            return await self._api_client.get_product_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def get_product(self, product_id: int) -> ShowProductWithRelations:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.get_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
        return ShowProductWithRelations.model_validate(product)

    async def platforms_list(self) -> list[PlatformDTO]:
        async with self._uow as uow:
            platforms = await uow.platforms_repo.list()
        return [PlatformDTO.model_validate(platform) for platform in platforms]

    async def categories_list(self) -> list[CategoryDTO]:
        async with self._uow as uow:
            categories = await uow.categories_repo.list()
        return [CategoryDTO.model_validate(category) for category in categories]

    async def delivery_methods_list(self) -> list[DeliveryMethodDTO]:
        async with self._uow as uow:
            delivery_methods = await uow.delivery_methods_repo.list()
        return [DeliveryMethodDTO.model_validate(method) for method in delivery_methods]

    async def update_product(
        self, product_id: int, dto: UpdateProductDTO
    ) -> ShowProduct:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.update_by_id(
                    product_id, dto, cast(str | None, dto.image)
                )
        except AlreadyExistsError:
            params = {
                "name": dto.name,
                "category_id": dto.category.id if dto.category is not None else None,
                "platform_id": dto.platform.id if dto.platform is not None else None,
            }
            raise EntityAlreadyExistsError(
                self.entity_name, **{k: v for k, v in params.items() if v is not None}
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
