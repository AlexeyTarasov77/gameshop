import typing as t
from http import HTTPStatus

from core.ioc import Inject
from fastapi import APIRouter

from products import schemas
from products.domain.services import ProductsService

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/create", status_code=HTTPStatus.CREATED)
async def create_product(
    dto: schemas.CreateProductDTO,
    products_service: t.Annotated[ProductsService, Inject(ProductsService)],
) -> schemas.ShowProduct:
    print(products_service)
    try:
        product = await products_service.create_product(dto)
    except Exception as e:
        raise e
    return product
