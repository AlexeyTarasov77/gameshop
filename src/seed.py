from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from gateways.db.exceptions import PostgresExceptionsMapper
import random
import asyncio
from gateways.db.main import SqlAlchemyDatabase
from gateways.db.models import SqlAlchemyBaseModel
from gateways.db.repository import SqlAlchemyRepository
from faker import Faker
from news.models import News
from products.models import Category, Platform, Product, DeliveryMethod
from users.hashing import BcryptHasher
from users.models import User
from orders.models import Order, OrderItem, OrderStatus
import os

fake = Faker()
dsn = os.environ.get("DB_DSN") or input("Введите dsn: ")
db = SqlAlchemyDatabase(dsn, PostgresExceptionsMapper)


def _call_optional(func: Callable[..., Any]):
    return func() if fake.boolean() else None


def _get_repo(model: type[SqlAlchemyBaseModel]) -> SqlAlchemyRepository:
    session = db.session_factory()
    repo = SqlAlchemyRepository[model](session)
    return repo


async def _create_entities[T: SqlAlchemyBaseModel](
    model: type[T], data_generator: Callable[[], dict], n: int
) -> list[T]:
    repo = _get_repo(model)
    entities = [model(**data_generator()) for _ in range(n)]
    async with repo.session as session:
        session.add_all(entities)
        await session.commit()
    return entities
    # coros = [repo.create(**data_generator()) for _ in range(n)]
    # return await asyncio.gather(*coros)


async def _create_model_with_name_and_url[T: SqlAlchemyBaseModel](
    n: int, model: type[T]
) -> list[T]:
    def data_generator():
        return {"name": fake.name(), "url": fake.url()}

    return await _create_entities(model, data_generator, n)


async def create_categories(n: int):
    return await _create_model_with_name_and_url(n, Category)


async def create_platforms(n: int):
    return await _create_model_with_name_and_url(n, Platform)


async def create_delivery_methods(n: int):
    return await _create_model_with_name_and_url(n, DeliveryMethod)


async def create_products(
    n: int,
    platforms: list[Platform],
    categories: list[Category],
    delivery_methods: list[DeliveryMethod],
):
    def data_generator():
        return {
            "name": fake.name(),
            "description": fake.sentence(),
            "platform": random.choice(platforms),
            "category": random.choice(categories),
            "delivery_method": random.choice(delivery_methods),
            "image_url": fake.image_url(),
            "regular_price": Decimal(random.randint(100, 1000)),
            "discount": random.randint(0, 100),
            "discount_valid_to": _call_optional(
                lambda: (
                    fake.date_time_between(
                        datetime.now(), timedelta(days=30)
                    ).isoformat()
                )
            ),
        }

    return await _create_entities(Product, data_generator, n)


async def create_users(n: int):
    def data_generator():
        return {
            "email": fake.email(),
            "password_hash": BcryptHasher().hash(fake.password(8)),
            "photo_url": _call_optional(fake.image_url),
            "is_active": fake.boolean(),
        }

    return await _create_entities(User, data_generator, n)


async def create_orders(n: int, users: list[User], products: list[Product]):
    def data_generator():
        return {
            "customer_name": fake.user_name(),
            "customer_email": fake.email(),
            "customer_phone": fake.phone_number(),
            "status": random.choice(list(OrderStatus)),
            "user": _call_optional(lambda: random.choice(users)),
            "items": [
                OrderItem(
                    product=random.choice(products),
                    price=Decimal(random.randint(100, 1000)),
                    quantity=random.randint(1, 10),
                )
            ],
        }

    return await _create_entities(Order, data_generator, n)


async def create_news(n: int):
    def data_generator():
        return {
            "title": fake.sentence(),
            "description": fake.sentence(),
            "photo_url": _call_optional(fake.image_url),
        }

    return await _create_entities(News, data_generator, n)


async def main():
    print("Creating platforms, categories and delivery_methods...")
    platforms, categories, delivery_methods = await asyncio.gather(
        create_platforms(10), create_categories(10), create_delivery_methods(10)
    )
    print("Creating users and products...")
    users, products = await asyncio.gather(
        create_users(20), create_products(30, platforms, categories, delivery_methods)
    )
    print("Creating news and orders...")
    await asyncio.gather(create_orders(10, users, products), create_news(20))
    print("All entities have been succesfully created!")


if __name__ == "__main__":
    asyncio.run(main())
