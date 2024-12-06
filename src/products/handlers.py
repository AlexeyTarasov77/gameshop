import typing as t
from http import HTTPStatus

from core.http.exceptions import HttpExceptionsMapper
from core.ioc import Inject
from core.service import (
    ServiceError,
)
from fastapi import APIRouter, Form

from products import schemas
from products.domain.services import ProductsService

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/create", status_code=HTTPStatus.CREATED)
async def create_product(
    dto: t.Annotated[schemas.CreateProductDTO, Form()],
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
    dto: t.Annotated[schemas.UpdateProductDTO, Form()],
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
