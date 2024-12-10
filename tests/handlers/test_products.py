import asyncio
import random
import typing as t
from contextlib import suppress
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import zip_longest

import pytest
from handlers.conftest import client, db, faker
from sqlalchemy import select

from gateways.db.exceptions import NotFoundError
from gateways.db.repository import SqlAlchemyRepository
from products.handlers import router
from products.models import Product


def _gen_create_product_data():
    return {
        "name": faker.name(),
        "description": faker.sentence(),
        "regular_price": str(Decimal(faker.random_number(4))),
        "image_url": faker.image_url(),
        "delivery_method": random.choice(Product.DELIVERY_METHODS_CHOICES),
        "discount": random.randint(0, 100),
        "discount_valid_to": faker.date_time_between(datetime.now(), timedelta(days=30)).isoformat(),
        "category": {"id": random.randint(1, 3), "name": faker.company()},
        "platform": {"id": random.randint(1, 3), "name": faker.street_name()},
    }


@pytest.fixture()
def new_product():
    data = _gen_create_product_data()
    data["category_id"], data["platform_id"] = data["category"]["id"], data["platform"]["id"]
    data.pop("category")
    data.pop("platform")
    with asyncio.Runner() as runner:
        try:
            session = db.session_factory()
            repo = SqlAlchemyRepository(session)
            repo.model = Product
            product: Product = runner.run(repo.create(**data))
            runner.run(session.commit())
            yield product
            with suppress(NotFoundError):
                runner.run(repo.delete(id=product.id))
        finally:
            runner.run(session.close())


create_product_data = _gen_create_product_data()


@pytest.mark.parametrize(
    ["data", "expected_status"],
    [
        (create_product_data, 201),
        (create_product_data, 409),
        (
            {
                **_gen_create_product_data(),
                "discount_valid_to": str(datetime.now()),
            },
            422,
        ),
        (
            {
                **_gen_create_product_data(),
                "name": "",
            },
            422,
        ),
        (
            {
                **_gen_create_product_data(),
                "delivery_method": "unknown",
            },
            422,
        ),
        (
            {
                **_gen_create_product_data(),
                "regular_price": -100,
            },
            422,
        ),
        (
            {
                **_gen_create_product_data(),
                "discount": -100,
            },
            422,
        ),
        (
            {
                **_gen_create_product_data(),
                "image_url": "invalid",
            },
            422,
        ),
    ],
)
def test_create_product(data: dict[str, t.Any], expected_status: int):
    resp = client.post(f"{router.prefix}/create", json=data)
    resp_data = resp.json()
    assert resp.status_code == expected_status
    if expected_status == 201:
        assert resp_data["name"] == data["name"]
        assert resp_data["description"] == data["description"]
        assert resp_data["regular_price"] == data["regular_price"]
        assert resp_data["discount"] == data["discount"]
        assert resp_data["category_id"] == data["category"]["id"]
        assert resp_data["platform_id"] == data["platform"]["id"]


@pytest.mark.parametrize(
    ["data", "expected_status", "product_id"],
    [
        ({"name": faker.name()}, 200, None),
        ({"name": faker.name()}, 404, 999),
        ({}, 400, None),
        ({"category": {"id": 999, "name": faker.name()}}, 400, None),
        ({"discount": -100}, 422, None),
        ({"discount_valid_to": None}, 200, None),
        ({"name": None}, 422, None),
        ({"name": faker.name()}, 422, -1),
    ],
)
def test_update_product(
    data: dict[str, t.Any], new_product: Product, expected_status: int, product_id: int | None
):
    product_id = product_id or new_product.id
    resp = client.put(f"{router.prefix}/update/{product_id}", json=data)
    resp_data = resp.json()
    assert resp.status_code == expected_status
    if expected_status == 200:
        for resp_key, data_key in zip_longest(resp_data, data):
            if data_key is None:
                if resp_key in data:
                    continue
                product_val = getattr(new_product, resp_key)
                resp_val = resp_data[resp_key]
                if type(product_val) is datetime:
                    product_val = product_val.isoformat()
                else:
                    t = type(resp_val)
                    product_val = t(product_val)
                assert resp_val == product_val
            else:
                assert resp_data[data_key] == data[data_key]


@pytest.mark.parametrize(["expected_status", "product_id"], [(204, None), (404, 999), (422, -1)])
def test_delete_product(new_product: Product, expected_status: int, product_id: int | None):
    product_id = product_id or new_product.id
    resp = client.delete(f"{router.prefix}/delete/{product_id}")
    assert resp.status_code == expected_status
    if expected_status == 204:
        with asyncio.Runner() as runner:
            try:
                session = db.session_factory()
                stmt = select(Product.id).filter_by(id=new_product.id)
                res = runner.run(session.execute(stmt))
                assert len(res.scalars().all()) == 0
            finally:
                runner.run(session.close())
