from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from core.dependencies import PaginationDep
from core.ioc import Inject
from core.pagination import PaginatedResponse
from sales.domain.interfaces import ExchangeRatesMappingDTO
from sales.domain.services import SalesService
from sales.schemas import SetExchangeRateDTO, ProductOnSaleDTO, SalesFilterDTO
from users.dependencies import require_admin


router = APIRouter(prefix="/sales", tags=["sales", "products"])

SalesServiceDep = Annotated[SalesService, Inject(SalesService)]


@router.get("/")
async def get_current_sales(
    pagination_params: PaginationDep,
    sales_service: SalesServiceDep,
    dto: Annotated[SalesFilterDTO, Query()] = {},  # type: ignore
) -> PaginatedResponse[ProductOnSaleDTO]:
    sales, total_records = await sales_service.get_current_sales(
        dto,
        pagination_params,
    )
    return PaginatedResponse.new_response(sales, total_records, pagination_params)


@router.get("/{product_id}")
async def get_product_on_sale(
    product_id: UUID,
    sales_service: SalesServiceDep,
) -> ProductOnSaleDTO:
    return await sales_service.get_product_on_sale(product_id)


@router.get("/exchange-rates/steam")
async def get_steam_exchange_rates(
    sales_service: SalesServiceDep,
) -> ExchangeRatesMappingDTO:
    return await sales_service.get_steam_exchange_rates()


@router.post(
    "/exchange-rates/set",
    dependencies=[Depends(require_admin)],
)
async def set_exchange_rate(dto: SetExchangeRateDTO, sales_service: SalesServiceDep):
    await sales_service.set_exchange_rate(dto)
    return {"success": True}


@router.get(
    "/exchange-rates/get",
    dependencies=[Depends(require_admin)],
)
async def get_exchange_rates(sales_service: SalesServiceDep) -> ExchangeRatesMappingDTO:
    return await sales_service.get_exchange_rates()


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_product_on_sale(
    product_id: UUID,
    sales_service: SalesServiceDep,
) -> None:
    return await sales_service.delete_product_on_sale(product_id)
