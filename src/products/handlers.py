from collections.abc import Sequence
import typing as t

from core.exception_mappers import HttpExceptionsMapper
from core.schemas import EntityIDParam
from core.pagination import PaginatedResponse
from core.dependencies import PaginationDep, restrict_content_type
from core.ioc import Inject, Resolve
from core.schemas import Base64IntOptionalIDParam
from core.services.exceptions import MappedServiceError
from fastapi import APIRouter, Form, HTTPException, Depends, status

from products import schemas
from products.domain.services import ProductsService
from users.dependencies import require_admin

router = APIRouter(prefix="/products", tags=["products"])

ProductsServiceDep = t.Annotated[ProductsService, Inject(ProductsService)]


class ProductsPaginatedResponse(PaginatedResponse):
    products: list[schemas.ShowProductWithRelations]


@router.get("/")
async def list_products(
    pagination_params: PaginationDep,
    products_service: ProductsServiceDep,
    query: str | None = None,
    category_id: Base64IntOptionalIDParam = None,
    discounted: bool | None = None,
    in_stock: bool | None = None,
) -> ProductsPaginatedResponse:
    try:
        products, total_records = await products_service.list_products(
            query,
            int(category_id) if category_id else None,
            discounted,
            in_stock,
            pagination_params,
        )
    except MappedServiceError as e:
        Resolve(HttpExceptionsMapper).map_and_raise(e)
    return ProductsPaginatedResponse(
        products=products,
        total_records=total_records,
        total_on_page=len(products),
        first_page=1,
        **pagination_params.model_dump(),
    )


class SalesPaginatedResponse(PaginatedResponse):
    sales: Sequence[schemas.ProductOnSaleDTO]


@router.get("/sales")
async def get_current_sales(
    pagination_params: PaginationDep, products_service: ProductsServiceDep
):
    try:
        products, total_records = await products_service.get_current_sales(
            pagination_params,
        )
    except MappedServiceError as e:
        Resolve(HttpExceptionsMapper).map_and_raise(e)
    return SalesPaginatedResponse(
        sales=products,
        total_records=total_records,
        total_on_page=len(products),
        first_page=1,
        **pagination_params.model_dump(),
    )


@router.get("/detail/{product_id}")
async def get_product(
    product_id: EntityIDParam, products_service: ProductsServiceDep
) -> dict[str, schemas.ShowProductWithRelations]:
    try:
        product = await products_service.get_product(int(product_id))
    except MappedServiceError as e:
        Resolve(HttpExceptionsMapper).map_and_raise(e)
    return {"product": product}


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
    try:
        product = await products_service.create_product(dto)
    except MappedServiceError as e:
        Resolve(HttpExceptionsMapper).map_and_raise(e)
    return product


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
    if not dto.model_dump(exclude_unset=True):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Nothing to update. No data provided"
        )
    try:
        product = await products_service.update_product(int(product_id), dto)
    except MappedServiceError as e:
        Resolve(HttpExceptionsMapper).map_and_raise(e)
    return product


@router.delete(
    "/delete/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_product(
    product_id: EntityIDParam,
    products_service: ProductsServiceDep,
) -> None:
    try:
        await products_service.delete_product(int(product_id))
    except MappedServiceError as e:
        Resolve(HttpExceptionsMapper).map_and_raise(e)


@router.get("/platforms")
async def platforms_list(
    products_service: ProductsServiceDep,
) -> dict[str, list[schemas.PlatformDTO]]:
    return {"platforms": await products_service.platforms_list()}


@router.get("/categories")
async def categories_list(
    products_service: ProductsServiceDep,
) -> dict[str, list[schemas.CategoryDTO]]:
    return {"categories": await products_service.categories_list()}


@router.get("/delivery-methods")
async def delivery_methods_list(
    products_service: ProductsServiceDep,
) -> dict[str, list[schemas.DeliveryMethodDTO]]:
    return {"delivery_methods": await products_service.delivery_methods_list()}
