import typing as t

from core.ioc import Inject
from core.schemas import EntityIDParam, require_dto_not_empty
from core.pagination import PaginatedResponse
from core.dependencies import PaginationDep, restrict_content_type
from fastapi import APIRouter, Form, Depends, Query, status
from gateways.currency_converter import (
    ExchangeRatesMappingDTO,
    SetExchangeRateDTO,
)
from products import schemas
from products.domain.services import ProductsService
from users.dependencies import require_admin

router = APIRouter(prefix="/products", tags=["products"])

ProductsServiceDep = t.Annotated[ProductsService, Inject(ProductsService)]


@router.get("/")
async def list_products(
    pagination_params: PaginationDep,
    products_service: ProductsServiceDep,
    dto: t.Annotated[schemas.ListProductsFilterDTO, Query()] = {},  # type: ignore
) -> PaginatedResponse[schemas.ShowProductExtended]:
    products, total_records = await products_service.list_products(
        dto,
        pagination_params,
    )
    return PaginatedResponse.new_response(products, total_records, pagination_params)


@router.get("/detail/{product_id}")
async def get_product(
    product_id: EntityIDParam, products_service: ProductsServiceDep
) -> schemas.ShowProductExtended:
    return await products_service.get_product(int(product_id))


@router.patch("/update-prices", dependencies=[Depends(require_admin)])
async def update_prices(
    dto: schemas.UpdatePricesDTO, products_service: ProductsServiceDep
) -> schemas.UpdatePricesResDTO:
    return await products_service.update_prices(dto)


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        restrict_content_type("multipart/form-data"),
        Depends(require_admin),
    ],
)
async def create_product(
    dto: t.Annotated[schemas.CreateProductDTO, Form(media_type="multipart/form-data")],
    products_service: ProductsServiceDep,
) -> schemas.ShowProduct:
    return await products_service.create_product(dto)


@router.put(
    "/update/{product_id}",
    dependencies=[
        restrict_content_type("multipart/form-data"),
        Depends(require_admin),
    ],
)
async def update_product(
    product_id: EntityIDParam,
    dto: t.Annotated[schemas.UpdateProductDTO, Form(media_type="multipart/form-data")],
    products_service: ProductsServiceDep,
) -> schemas.ShowProduct:
    require_dto_not_empty(dto)
    return await products_service.update_product(int(product_id), dto)


@router.delete(
    "/delete/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_product(
    product_id: EntityIDParam,
    products_service: ProductsServiceDep,
) -> None:
    await products_service.delete_product(int(product_id))


@router.get("/platforms")
async def platforms_list(
    products_service: ProductsServiceDep,
) -> schemas.PlatformsListDTO:
    return await products_service.platforms_list()


@router.get("/categories")
async def categories_list(
    products_service: ProductsServiceDep,
) -> schemas.CategoriesListDTO:
    return await products_service.categories_list()


@router.get("/delivery-methods")
async def delivery_methods_list(
    products_service: ProductsServiceDep,
) -> schemas.DeliveryMethodsListDTO:
    return await products_service.delivery_methods_list()


@router.get(
    "/exchange-rates/steam",
    tags=["exchange-rates"],
)
async def get_steam_exchange_rates(
    products_service: ProductsServiceDep,
) -> ExchangeRatesMappingDTO:
    return await products_service.get_steam_exchange_rates()


@router.post(
    "/exchange-rates/set",
    tags=["exchange-rates"],
    dependencies=[Depends(require_admin)],
)
async def set_exchange_rate(
    dto: SetExchangeRateDTO, products_service: ProductsServiceDep
):
    await products_service.set_exchange_rate(dto)
    return {"success": True}


@router.get(
    "/exchange-rates/get",
    tags=["exchange-rates"],
    dependencies=[Depends(require_admin)],
)
async def get_exchange_rates(
    products_service: ProductsServiceDep,
) -> ExchangeRatesMappingDTO:
    return await products_service.get_exchange_rates()
