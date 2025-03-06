from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Query

from core.dependencies import PaginationDep
from core.ioc import Inject
from sales.domain.services import SalesService
from sales.schemas import SalesFilterDTO


router = APIRouter(prefix="/sales", tags=["sales", "products"])

SalesServiceDep = Annotated[SalesService, Inject(SalesService)]


# @router.get("/sales")
# async def get_current_sales(
#     pagination_params: PaginationDep,
#     sales_service: SalesServiceDep,
#     dto: Annotated[SalesFilterDTO, Query()],
# ):
#     sales, total_records = await sales_service.get_current_sales(
#         dto,
#         pagination_params,
#     )
#     return PaginatedResponse.new_response(sales, total_records, pagination_params)
#
#
# @router.get("/sales/{product_id}")
# async def get_product_on_sale(
#     product_id: UUID,
#     sales_service: SalesServiceDep,
# ) -> schemas.ProductOnSaleDTO:
#     return await sales_service.get_product_on_sale(int(product_id))
#
#
# @router.delete("/sales/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_product_on_sale(
#     product_id: UUID,
#     sales_service: SalesServiceDep,
# ) -> None:
#     return await sales_service.delete_product_on_sale(int(product_id))
