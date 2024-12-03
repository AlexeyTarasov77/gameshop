import typing as t

from core.ioc import Inject
from fastapi import APIRouter
from products import schemas
from products.domain.services import ProductsService

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/create")
def create_product(
    dto: schemas.CreateProductDTO,
    products_service: t.Annotated[ProductsService, Inject(ProductsService)],
):
    try:
        product = products_service.create_product(dto)
    except Exception as e:
        print(e)
        ...
    return product
