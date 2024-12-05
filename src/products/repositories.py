from core.http.utils import FilePath
from db.repository import SqlAlchemyRepository

from products.models import Product
from products.schemas import CreateProductDTO


class ProductsRepository(SqlAlchemyRepository[Product]):
    model = Product

    async def create(self, dto: CreateProductDTO, image_url: FilePath) -> Product:
        try:
            return await super().create(
                image_url=str(image_url),
                **dto.model_dump(
                    exclude={
                        "image",
                    }
                ),
            )
        except Exception as e:
            print("!EXC: ", type(e))
