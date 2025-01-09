import asyncio
import random
from contextlib import suppress
from datetime import datetime, timedelta
from decimal import Decimal
import typing as t
import pytest
from helpers import base64_to_int, check_paginated_response, is_base64
from sqlalchemy import select
from handlers.test_products import new_product
from handlers.test_users import new_user
from gateways.db.exceptions import NotFoundError
from gateways.db.repository import SqlAlchemyRepository
from handlers.conftest import client, db, fake
from orders.handlers import router
from orders.models import Order, OrderStatus
from products.models import Product
from users.domain.services import UsersService
from users.models import User
from users.schemas import UserSignInDTO


def _gen_order_data() -> dict[str, str]:
    return {
        "name": fake.user_name(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "tg_username": fake.user_name(),
    }


def _gen_order_item_data() -> dict:
    session = db.session_factory()
    product_ids = asyncio.run(session.execute(select(Product.id))).scalars().all()
    return {
        "price": str(Decimal(fake.random_int(100))),
        "quantity": fake.random_int(1, 10),
        "product_id": random.choice(product_ids),
    }


@pytest.fixture
def new_order(new_user: User):  # noqa
    session = db.session_factory()
    repo = SqlAlchemyRepository(session)
    repo.model = Order
    with asyncio.Runner() as runner:
        try:
            order = runner.run(repo.create(**_gen_order_data(), user_id=new_user.id))
            runner.run(session.commit())
            yield order
            with suppress(NotFoundError):
                runner.run(repo.delete(id=order.id))
                runner.run(session.commit())
        finally:
            runner.run(session.close())


def _gen_order_create_data():
    return {
        "user": _gen_order_data(),
        "cart": [_gen_order_item_data() for _ in range(random.randint(1, 10))],
    }


# TODO: add more test cases
@pytest.mark.parametrize(
    ["data", "expected_status", "with_auth"],
    [
        (_gen_order_create_data(), 201, True),
        ({**_gen_order_create_data(), "customer_email": "invalid"}, 422, True),
        ({**_gen_order_create_data(), "customer_phone": "invalid"}, 422, True),
        ({**_gen_order_create_data(), "customer_phone": "123"}, 422, True),
        ({**_gen_order_create_data(), "customer_name": "Vasya12"}, 422, True),
    ],
)
def test_create_order(
    new_user: User,
    new_product: Product,
    data: dict[str, t.Any],
    expected_status: int,
    with_auth: bool,
):
    headers = None
    # if with_auth:
    #     users_service = t.cast(UsersService, get_container().resolve(UsersService))
    #     token = asyncio.run(
    #         users_service.signin(
    #             UserSignInDTO(
    #                 email=new_user.email, password=new_user.password_hash.decode()
    #             )
    #         )
    #     )
    #     headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(f"{router.prefix}/create", json=data, headers=headers)
    resp_data = resp.json()
    assert resp.status_code == expected_status
    if expected_status == 201:
        print("RESP_DATA", resp_data)
        assert is_base64(resp_data["id"])
        assert resp_data["status"] == OrderStatus.PENDING.value
        assert (
            datetime.now() - timedelta(seconds=10)
            < datetime.fromisoformat(resp_data["order_date"])
            < datetime.now()
        )
