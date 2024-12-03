from core.service import BaseService
from products.models import Product
from products.schemas import CreateProductDTO


class ProductsService(BaseService):
    def create_product(self, dto: CreateProductDTO) -> Product: ...
