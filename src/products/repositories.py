from db.repository import SqlAlchemyRepository

from products.models import Product
from products.schemas import CreateProductDTO


class ProductsRepository(SqlAlchemyRepository[Product]):
    model = Product

    async def create(self, dto: CreateProductDTO) -> Product:
        dto.image_url = str(dto.image_url)
        pr = await super().create(**dto.model_dump())
        print("pr", pr, pr.id)
        return pr
