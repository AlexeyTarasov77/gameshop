import typing as t
from http import HTTPStatus

from core.ioc import Inject
from core.service import EntityAlreadyExistsError, EntityRelatedResourceNotFoundError
from fastapi import APIRouter, Form, HTTPException

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
    except (EntityRelatedResourceNotFoundError, EntityAlreadyExistsError) as e:
        raise HTTPException(HTTPStatus.CONFLICT, e.msg) from e
    return product


@router.put("/update/{product_id}")
async def update_product(
    product_id: int,
    dto: t.Annotated[schemas.UpdateProductDTO, Form()],
    products_service: t.Annotated[ProductsService, Inject(ProductsService)],
) -> schemas.ShowProduct:
    try:
        product = await products_service.update_product(product_id, dto)
    except (EntityRelatedResourceNotFoundError, EntityAlreadyExistsError) as e:
        raise HTTPException(HTTPStatus.CONFLICT, e.msg) from e
    return product
