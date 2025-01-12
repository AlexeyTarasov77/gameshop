import random
from datetime import datetime, timedelta
from decimal import Decimal
import typing as t
import pytest
from sqlalchemy import select
from handlers.test_products import new_product  # noqa
from handlers.test_users import new_user  # noqa
from handlers.conftest import client, db, fake
from orders.handlers import router
from orders.models import Order, OrderStatus
from products.models import Product
from handlers.helpers import (
    create_model_obj,
    base64_to_int,
    get_model_obj,
    is_base64,
)
from users.models import User


def _gen_customer_data() -> dict[str, str]:
    return {
        "name": fake.first_name_male(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "tg_username": fake.user_name(),
    }


def _gen_order_data() -> dict[str, str]:
    customer_data = _gen_customer_data()
    data = {
        "customer_tg": customer_data.pop("tg_username"),
        **{"customer_" + k: v for k, v in customer_data.items()},
    }
    return data


def _gen_order_item_data() -> dict:
    with db.sync_engine.begin() as conn:
        product_ids = conn.execute(select(Product.id)).scalars().all()
    return {
        "price": str(Decimal(fake.random_int(100))),
        "quantity": fake.random_int(1, 10),
        "product_id": random.choice(product_ids),
    }


@pytest.fixture
def new_order(new_user: User):  # noqa
    yield from create_model_obj(Order, **_gen_order_data())


def _gen_order_create_data():
    return {
        "user": _gen_customer_data(),
        "cart": [_gen_order_item_data() for _ in range(random.randint(1, 10))],
    }


# TODO: add more test cases
@pytest.mark.parametrize(
    ["data", "expected_status", "with_auth"],
    [
        (_gen_order_create_data(), 201, True),
        (
            {
                **_gen_order_create_data(),
                "user": {**_gen_customer_data(), "email": "invalid"},
            },
            422,
            True,
        ),
        (
            {
                **_gen_order_create_data(),
                "user": {**_gen_customer_data(), "phone": "123"},
            },
            422,
            True,
        ),
        (
            {
                **_gen_order_create_data(),
                "user": {**_gen_customer_data(), "name": "Vasya12"},
            },
            422,
            True,
        ),
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
        assert is_base64(resp_data["id"])
        order_id = base64_to_int(resp_data["id"])
        assert resp_data["status"] == OrderStatus.PENDING.value
        assert (
            datetime.now() - timedelta(seconds=10)
            < datetime.fromisoformat(resp_data["order_date"])
            < datetime.now()
        )
        order = get_model_obj(Order, id=order_id)
        assert order is not None
        assert order.id == order_id
        assert order.status.value == resp_data["status"]


@pytest.mark.parametrize(
    ["expected_status", "order_id"], [(204, None), (404, 999999), (422, -1)]
)
def test_delete_order(new_order: Order, expected_status: int, order_id: int | None):
    order_id = order_id or new_order.id
    resp = client.delete(f"{router.prefix}/delete/{order_id}")
    assert resp.status_code == expected_status
    if expected_status == 204:
        assert get_model_obj(Order, id=new_order.id) is None


@pytest.mark.parametrize(
    ["data", "expected_status", "order_id"],
    [
        ({"status": random.choice(list(OrderStatus)).value}, 200, None),
        ({"status": "invalid"}, 422, None),
        ({"status": random.choice(list(OrderStatus)).value}, 404, 999999),
        ({"status": random.choice(list(OrderStatus)).value}, 422, -1),
        ({}, 422, None),
    ],
)
def test_update_order(
    new_order: Order, data: dict[str, int], expected_status: int, order_id: int | None
):
    order_id = order_id or new_order.id
    resp = client.patch(f"{router.prefix}/update/{order_id}", json=data)
    assert resp.status_code == expected_status
    resp_data = resp.json()
    if expected_status == 200:
        assert resp_data["status"] == data["status"]
