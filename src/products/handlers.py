import typing as t
from http import HTTPStatus

from core.exception_mappers import HttpExceptionsMapper
from core.schemas import EntityIDParam
from core.pagination import PaginatedResponse, PaginationDep
from core.ioc import Inject
from core.schemas import Base64IntOptionalIDParam
from core.services.exceptions import ServiceError
from fastapi import APIRouter, Form, HTTPException, Depends

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
) -> ProductsPaginatedResponse:
    try:
        products, total_records = await products_service.list_products(
            query, int(category_id) if category_id else None, pagination_params
        )
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return ProductsPaginatedResponse(
        products=products,
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
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return {"product": product}


@router.post(
    "/create", status_code=HTTPStatus.CREATED, dependencies=[Depends(require_admin)]
)
async def create_product(
    dto: t.Annotated[schemas.CreateProductDTO, Form()],
    products_service: ProductsServiceDep,
) -> schemas.ShowProduct:
    try:
        product = await products_service.create_product(dto)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return product


@router.put("/update/{product_id}", dependencies=[Depends(require_admin)])
async def update_product(
    product_id: EntityIDParam,
    dto: schemas.UpdateProductDTO,
    products_service: ProductsServiceDep,
) -> schemas.ShowProduct:
    if not dto.model_dump(exclude_unset=True):
        raise HTTPException(400, "Nothing to update. No data provided")
    try:
        product = await products_service.update_product(int(product_id), dto)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return product


@router.delete(
    "/delete/{product_id}", status_code=204, dependencies=[Depends(require_admin)]
)
async def delete_product(
    product_id: EntityIDParam,
    products_service: ProductsServiceDep,
) -> None:
    try:
        await products_service.delete_product(int(product_id))
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)


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
