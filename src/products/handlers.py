import typing as t
from http import HTTPStatus

from core.http.exceptions import HttpExceptionsMapper
from core.ioc import Inject
from core.service import ServiceError
from fastapi import APIRouter

from products import schemas
from products.domain.services import ProductsService

router = APIRouter(prefix="/products", tags=["products"])

# router.get("/")
# async def list_products(products_service: t.Annotated[ProductsService, Inject(ProductsService)]):
#     ...


@router.post("/create", status_code=HTTPStatus.CREATED)
async def create_product(
    dto: schemas.CreateProductDTO,
    products_service: t.Annotated[ProductsService, Inject(ProductsService)],
) -> schemas.ShowProduct:
    try:
        product = await products_service.create_product(dto)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return product


@router.put("/update/{product_id}")
async def update_product(
    product_id: int,
    dto: schemas.UpdateProductDTO,
    products_service: t.Annotated[ProductsService, Inject(ProductsService)],
) -> schemas.ShowProduct:
    try:
        product = await products_service.update_product(product_id, dto)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return product


@router.delete("/delete/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    products_service: t.Annotated[ProductsService, Inject(ProductsService)],
) -> None:
    try:
        await products_service.delete_product(product_id)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)


@router.get("/platforms")
async def platforms_list(
    products_service: t.Annotated[ProductsService, Inject(ProductsService)],
) -> dict[str, list[schemas.PlatformDTO]]:
    return {"platforms": await products_service.platforms_list()}


@router.get("/categories")
async def categories_list(
    products_service: t.Annotated[ProductsService, Inject(ProductsService)],
) -> dict[str, list[schemas.CategoryDTO]]:
    return {"categories": await products_service.categories_list()}


@router.get("/delivery-methods")
async def delivery_methods_list(
    products_service: t.Annotated[ProductsService, Inject(ProductsService)],
) -> dict[str, list[str]]:
    return {"delivery_methods": await products_service.delivery_methods_list()}
