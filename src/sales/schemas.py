from core.schemas import BaseDTO
from sales.models import ProductOnSaleCategory


class SalesFilterDTO(BaseDTO):
    category: ProductOnSaleCategory | None = None
    region: str | None = None
