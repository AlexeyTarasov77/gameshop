import asyncio
import random
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, TypeVar, Type

from faker import Faker

from core.ioc import Resolve
from gateways.db.sqlalchemy_gateway.main import SqlAlchemyClient
from gateways.db.sqlalchemy_gateway import SqlAlchemyBaseModel
from news.models import News
from orders.models import InAppOrder, InAppOrderItem, OrderStatus
from products.models import (
    Product,
    ProductCategory,
    ProductDeliveryMethod,
    ProductPlatform,
    RegionalPrice,
)
from users.hashing import BcryptHasher
from users.models import User

T = TypeVar("T", bound=SqlAlchemyBaseModel)


class SeedGenerator:
    def __init__(self):
        if not os.environ.get("MODE"):
            os.environ["MODE"] = "local"
        self.fake = Faker()
        self.db = Resolve(SqlAlchemyClient)

    def _call_optional(self, func: Callable[..., Any]):
        return func() if self.fake.boolean() else None

    async def _create_entities(
        self, model: Type[T], data_generator: Callable[[], dict], n: int
    ) -> list[T]:
        entities = [model(**data_generator()) for _ in range(n)]
        async with self.db.session_factory() as session:
            session.add_all(entities)
            await session.commit()
        return entities

    async def _create_products(
        self,
        n: int,
    ):
        def data_generator():
            data = {
                "name": self.fake.name(),
                "description": self.fake.sentence(),
                "platform": random.choice(list(ProductPlatform)),
                "category": random.choice(list(ProductCategory)),
                "delivery_method": random.choice(list(ProductDeliveryMethod)),
                "image_url": self.fake.image_url(),
                "prices": [
                    RegionalPrice(
                        base_price=random.randint(100, 100000),
                        region_code=self.fake.country_code(),
                    )
                    for _ in range(random.randint(1, 5))
                ],
                "discount": random.randint(0, 100),
                "deal_until": self._call_optional(
                    lambda: (
                        self.fake.date_time_between(
                            datetime.now(), datetime.now() + timedelta(days=30)
                        ).isoformat()
                    )
                ),
            }
            if (
                data["platform"] is ProductPlatform.STEAM
                and data["category"] is ProductCategory.GAMES
            ):
                data["sub_id"] = random.randint(100, 1000)
            return data

        return await self._create_entities(Product, data_generator, n)

    async def _create_orders(self, n: int, users: list[User], products: list[Product]):
        def data_generator():
            return {
                "customer_name": self.fake.user_name(),
                "customer_email": self.fake.email(),
                "customer_tg_username": self.fake.user_name(),
                "customer_phone": self.fake.phone_number(),
                "status": random.choice(list(OrderStatus)),
                "user": self._call_optional(lambda: random.choice(users)),
                "items": [
                    InAppOrderItem(
                        product=random.choice(products),
                        price=Decimal(random.randint(100, 1000)),
                        quantity=random.randint(1, 10),
                    )
                ],
            }

        return await self._create_entities(InAppOrder, data_generator, n)

    async def _create_news(self, n: int):
        def data_generator():
            return {
                "title": self.fake.sentence(),
                "description": self.fake.sentence(),
                "photo_url": self._call_optional(self.fake.image_url),
            }

        return await self._create_entities(News, data_generator, n)

    async def _create_users(self, n: int):
        def data_generator():
            return {
                "username": self.fake.user_name(),
                "email": self.fake.email(),
                "password_hash": BcryptHasher().hash(self.fake.password(8)),
                "photo_url": self._call_optional(self.fake.image_url),
                "is_active": self.fake.boolean(),
            }

        return await self._create_entities(User, data_generator, n)

    async def execute(self):
        print("Creating users and products...")
        users, products = await asyncio.gather(
            self._create_users(20),
            self._create_products(30),
        )
        print("Creating news and orders...")
        await asyncio.gather(
            self._create_orders(10, users, products), self._create_news(20)
        )
        print("All entities have been successfully created!")


if __name__ == "__main__":
    asyncio.run(SeedGenerator().execute())
