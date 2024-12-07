import typing as t
from pathlib import Path

from sqlalchemy import select

from gateways.db.repository import SqlAlchemyRepository
from products.models import Category, Platform, Product
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepository(SqlAlchemyRepository[Product]):
    model = Product

    async def create(self, dto: CreateProductDTO, image_url: Path) -> Product:
        return await super().create(
            image_url=str(image_url),
            **dto.model_dump(
                exclude={
                    "image",
                }
            ),
        )

    async def update(self, dto: UpdateProductDTO, image_url: Path = None, **filter_params) -> Product:
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


class PlatformsRepository(SqlAlchemyRepository[Platform]):
    model = Platform

    async def list_names(self) -> list[str]:
        res = await super().list(self.model.name)
        return t.cast(list[str], res)


class CategoriesRepository(SqlAlchemyRepository[Category]):
    model = Category

    async def list_names(self) -> list[str]:
        res = await super().list(self.model.name)
        return t.cast(list[str], res)
