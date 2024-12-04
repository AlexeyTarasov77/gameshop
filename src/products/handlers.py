import typing as t
from http import HTTPStatus

from core.ioc import Inject
from core.utils import save_upload_file
from fastapi import APIRouter, Form

from products import schemas
from products.domain.services import ProductsService

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/create", status_code=HTTPStatus.CREATED)
async def create_product(
    dto: t.Annotated[schemas.CreateProductDTO, Form()],
    products_service: t.Annotated[ProductsService, Inject(ProductsService)],
) -> schemas.ShowProduct:
    uploaded_to = await save_upload_file(dto.image)
    print("!!", uploaded_to)
    try:
        product = await products_service.create_product(dto, uploaded_to)
    except Exception as e:
        raise e
    return product
