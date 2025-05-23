from contextlib import suppress
import random
from datetime import datetime, timedelta
from decimal import Decimal
import typing as t
import pytest
from sqlalchemy import select
from core.ioc import Resolve
from handlers.test_products import new_product  # noqa
from handlers.test_users import new_user  # noqa
from handlers.conftest import client, db, fake
from orders.handlers import router
from orders.models import InAppOrder, InAppOrderItem, OrderStatus
from products.models import Product
from handlers.helpers import (
    create_model_obj,
    base64_to_int,
    get_model_obj,
    is_base64,
    check_paginated_response,
    pagination_test_cases,
)
from users.domain.interfaces import StatelessTokenProviderI
from users.models import User

if t.TYPE_CHECKING:
    from _typeshed import SupportsNext


def _gen_customer_data() -> dict[str, str]:
    return {
        "name": fake.first_name_male(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "tg_username": fake.user_name(),
    }


def _gen_order_item_data(order_id: int | None = None) -> dict:
    with db.sync_engine.begin() as conn:
        product_ids = conn.execute(select(Product.id)).scalars().all()
    data = {
        "price": str(Decimal(fake.random_int(100))),
        "quantity": fake.random_int(1, 10),
        "product_id": random.choice(product_ids),
    }
    if order_id:
        data["order_id"] = order_id
    return data


def _gen_order_data() -> dict[str, str]:
    customer_data = _gen_customer_data()
    data = {**{"customer_" + k: v for k, v in customer_data.items()}}
    return data


@pytest.fixture
def new_order(new_user: User):  # noqa
    data = _gen_order_data()
    order_coro = create_model_obj(InAppOrder, **data, user_id=new_user.id)
    order = next(order_coro)
    items_coros: list[SupportsNext] = [
        create_model_obj(InAppOrderItem, **_gen_order_item_data(order.id))
        for _ in range(random.randint(1, 10))
    ]
    [next(coro) for coro in items_coros]
    yield order
    # cleanup order and its items
    with suppress(StopIteration):
        [next(coro) for coro in items_coros]
        next(order_coro)


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
                "cart": [],
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
    new_user: User,  # noqa
    new_product: Product,  # noqa
    data: dict[str, t.Any],
    expected_status: int,
    with_auth: bool,
):
    # TODO: include auth headers
    resp = client.post(f"{router.prefix}/create", json=data)
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
        order = get_model_obj(InAppOrder, id=order_id)
        assert order is not None
        assert order.id == order_id
        assert order.status.value == resp_data["status"]


@pytest.mark.parametrize(
    ["expected_status", "order_id"], [(204, None), (404, 999999), (422, -1)]
)
def test_delete_order(
    new_order: InAppOrder, expected_status: int, order_id: int | None
):
    order_id = order_id or new_order.id
    resp = client.delete(f"{router.prefix}/delete/{order_id}")
    assert resp.status_code == expected_status
    if expected_status == 204:
        assert get_model_obj(InAppOrder, id=new_order.id) is None


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
    new_order: InAppOrder,
    data: dict[str, int],
    expected_status: int,
    order_id: int | None,
):
    order_id = order_id or new_order.id
    resp = client.patch(f"{router.prefix}/update/{order_id}", json=data)
    assert resp.status_code == expected_status
    resp_data = resp.json()
    if expected_status == 200:
        assert resp_data["status"] == data["status"]


@pytest.mark.parametrize(
    ["expected_status", "order_id"], [(200, None), (422, -1), (404, 999999)]
)
def test_get_order(new_order: InAppOrder, expected_status: int, order_id: int | None):
    order_id = order_id or new_order.id
    resp = client.get(f"{router.prefix}/detail/{order_id}")
    assert resp.status_code == expected_status
    if expected_status == 200:
        resp_data = resp.json()
        assert "user" in resp_data["customer"]
        assert "items" in resp_data
        assert "product" in resp_data["items"][0]
        assert Decimal(resp_data["total"]) == sum(
            Decimal(item["total_price"]) for item in resp_data["items"]
        )
        if user := resp_data["customer"].get("user"):
            assert base64_to_int(user["id"]) == new_order.user_id
        resp_order_id = base64_to_int(resp_data["id"])
        assert resp_order_id == new_order.id


@pytest.mark.parametrize(
    ["expected_status", "params", "with_user_id", "expired_token"],
    [
        (200, None, True, False),
        (200, {"page_size": 5, "page_num": 1}, True, False),
        (401, {"page_size": 5, "page_num": 1}, True, True),
        (401, None, False, False),
        (401, None, True, True),
        (422, {"page_size": 0}, True, False),
        (422, {"page_num": 0}, True, False),
    ],
)
def test_list_orders_for_user(
    new_order: InAppOrder,
    new_user: User,  # noqa
    expected_status: int,
    params: dict[str, int] | None,
    with_user_id: bool,
    expired_token: bool,
):
    headers = {}
    if with_user_id:
        token_provider = Resolve(StatelessTokenProviderI)
        token = token_provider.new_token(
            {"uid": new_user.id}, timedelta(days=(-1 if expired_token else 1))
        )
        headers["Authorization"] = f"Bearer {token}"
    resp = client.get(f"{router.prefix}/list-for-user", params=params, headers=headers)
    assert resp.status_code == expected_status
    resp_data = resp.json()
    if expected_status == 200:
        check_paginated_response("orders", resp_data, params)
        for order in resp_data["orders"]:
            assert "product" in order["items"][0]
            assert order["total"] == str(
                sum([Decimal(item["total_price"]) for item in order["items"]])
            )
            if user := order["customer"].get("user"):
                assert base64_to_int(user["id"]) == new_user.id


@pytest.mark.parametrize(["expected_status", "params"], pagination_test_cases)
def test_list_all_orders(
    new_order: InAppOrder,
    new_user: User,  # noqa
    expected_status: int,
    params: dict[str, int] | None,
):
    resp = client.get(f"{router.prefix}/list", params=params)
    assert resp.status_code == expected_status
    resp_data = resp.json()
    if expected_status == 200:
        for order in resp_data["orders"]:
            assert order["total"] == str(
                sum([Decimal(item["total_price"]) for item in order["items"]])
            )
        check_paginated_response("orders", resp_data, params)
