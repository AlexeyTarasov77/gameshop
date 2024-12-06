from core.http.utils import FilePath
from db.repository import SqlAlchemyRepository

from products.models import Product
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepository(SqlAlchemyRepository[Product]):
    model = Product

    async def create(self, dto: CreateProductDTO, image_url: FilePath) -> Product:
        return await super().create(
            image_url=str(image_url),
            **dto.model_dump(
                exclude={
                    "image",
                }
            ),
        )

    async def update(
        self, dto: UpdateProductDTO, image_url: FilePath = None, **filter_params
    ) -> Product:
        data = dto.model_dump(
            exclude={
                "image",
            },
            exclude_unset=True,
        )
        if image_url:
            data["image_url"] = str(image_url)
        return await super().update(
            data,
            **filter_params,
        )

    async def delete(self, product_id: int) -> None:
        await super().delete(id=product_id)
