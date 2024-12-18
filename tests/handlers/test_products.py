import asyncio
import base64
import math
import random
import typing as t
from contextlib import suppress
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import zip_longest

import pytest
from gateways.db.exceptions import NotFoundError
from gateways.db.repository import SqlAlchemyRepository
from helpers import is_base64
from products.handlers import router
from products.models import Product
from sqlalchemy import Result, select, text

from handlers.conftest import client, db, fake


def _gen_product_data(encode_ids: bool = True) -> dict[str, str | int | dict]:
    session = db.session_factory()
    with asyncio.Runner() as runner:
        try:
            res: Result = runner.run(
                session.execute(
                    text(
                        "SELECT c.id, p.id, dm.id FROM category c, platform p, delivery_method dm"
                    )
                )
            )
            relation_ids = random.choice(res.unique().all())
            if encode_ids:
                relation_ids = [
                    base64.b64encode(str(n).encode()).decode() for n in relation_ids
                ]
            category_id, platform_id, delivery_method_id = relation_ids
        finally:
            runner.run(session.close())
    return {
        "name": fake.name(),
        "description": fake.sentence(),
        "regular_price": str(Decimal(fake.random_number(4))),
        "image_url": fake.image_url(),
        "discount": random.randint(0, 100),
        "discount_valid_to": fake.date_time_between(
            datetime.now(), timedelta(days=30)
        ).isoformat(),
        "category": {"id": category_id, "name": fake.company(), "url": fake.url()},
        "platform": {"id": platform_id, "name": fake.street_name(), "url": fake.url()},
        "delivery_method": {
            "id": delivery_method_id,
            "name": fake.street_name(),
            "url": fake.url(),
        },
    }


def _decode_base64(s: str) -> str:
    return base64.b64decode(s).decode()


@pytest.fixture
def new_product():
    data = _gen_product_data(encode_ids=False)
    data["category_id"], data["platform_id"], data["delivery_method_id"] = (
        data["category"]["id"],
        data["platform"]["id"],
        data["delivery_method"]["id"],
    )
    data.pop("category")
    data.pop("platform")
    data.pop("delivery_method")
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
                runner.run(session.commit())
        finally:
            runner.run(session.close())


create_product_data = _gen_product_data()


@pytest.mark.parametrize(
    ["data", "expected_status"],
    [
        (create_product_data, 201),
        (_gen_product_data(False), 201),
        (create_product_data, 409),
        (
            {
                **_gen_product_data(),
                "discount_valid_to": str(datetime.now()),
            },
            422,
        ),
        (
            {
                **_gen_product_data(),
                "name": "",
            },
            422,
        ),
        (
            {
                **_gen_product_data(),
                "category": {"id": 0},
            },
            422,
        ),
        (
            {
                **_gen_product_data(),
                "regular_price": -100,
            },
            422,
        ),
        (
            {
                **_gen_product_data(),
                "discount": -100,
            },
            422,
        ),
        (
            {
                **_gen_product_data(),
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
        assert is_base64(resp_data["category_id"])
        assert is_base64(resp_data["delivery_method_id"])
        assert is_base64(resp_data["platform_id"])


@pytest.mark.parametrize(
    ["data", "expected_status", "product_id"],
    [
        ({"name": fake.name()}, 200, None),
        ({"name": fake.name()}, 404, 999999),
        ({}, 400, None),
        ({"category": {"id": 999999}}, 400, None),
        ({"discount": -100}, 422, None),
        ({"discount_valid_to": None}, 200, None),
        ({"name": None}, 422, None),
        ({"name": fake.name()}, 422, -1),
    ],
)
def test_update_product(
    data: dict[str, t.Any],
    new_product: Product,
    expected_status: int,
    product_id: int | None,
):
    product_id = product_id or new_product.id
    resp = client.put(f"{router.prefix}/update/{product_id}", json=data)
    resp_data = resp.json()
    assert resp.status_code == expected_status
    if expected_status == 200:
        assert is_base64(resp_data["id"])
        assert is_base64(resp_data["category_id"])
        assert is_base64(resp_data["platform_id"])
        assert is_base64(resp_data["delivery_method_id"])

        resp_data["id"] = int(_decode_base64(resp_data["id"]))
        resp_data["category_id"] = int(_decode_base64(resp_data["category_id"]))
        resp_data["platform_id"] = int(_decode_base64(resp_data["platform_id"]))
        resp_data["delivery_method_id"] = int(
            _decode_base64(resp_data["delivery_method_id"])
        )

        for resp_key, data_key in zip_longest(resp_data, data):
            if data_key is None:
                if resp_key in data:
                    continue
                product_val = getattr(new_product, resp_key)
                resp_val = resp_data[resp_key]
                if type(product_val) is datetime:
                    product_val = product_val.isoformat()
                else:
                    product_val = type(resp_val)(product_val)
                assert resp_val == product_val
            else:
                assert resp_data[data_key] == data[data_key]


@pytest.mark.parametrize(
    ["expected_status", "product_id"], [(204, None), (404, 999), (422, -1)]
)
def test_delete_product(
    new_product: Product, expected_status: int, product_id: int | None
):
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


@pytest.mark.parametrize(
    ["expected_status", "params"],
    [
        (200, None),
        (200, {"page_size": 5, "page_num": 1}),
        (422, {"page_size": 0}),
        (422, {"page_num": 0}),
    ],
)
def test_list_products(expected_status: int, params: dict[str, int] | None):
    resp = client.get(f"{router.prefix}/", params=params)
    assert resp.status_code == expected_status
    resp_data = resp.json()
    if expected_status == 200:
        assert "products" in resp_data
        assert "page_size" in resp_data
        assert "page_num" in resp_data
        assert "total_records" in resp_data
        assert (
            "total_on_page" in resp_data
            and resp_data["total_on_page"] <= resp_data["page_size"]
        )
        assert "first_page" in resp_data and resp_data["first_page"] == 1
        assert "last_page" in resp_data and resp_data["last_page"] == math.ceil(
            resp_data["total_records"] / resp_data["page_size"]
        )
        products = resp_data["products"]
        assert len(products) == resp_data["total_on_page"]
        if params:
            if params.get("page_size"):
                assert resp_data["page_size"] == params["page_size"]
            if params.get("page_num"):
                assert resp_data["page_num"] == params["page_num"]


@pytest.mark.parametrize(
    ["expected_status", "product_id"], [(200, None), (422, -1), (404, 999999)]
)
def test_get_product(
    new_product: Product, expected_status: int, product_id: int | None
):
    product_id = product_id or new_product.id
    resp = client.get(f"{router.prefix}/detail/{product_id}")
    assert resp.status_code == expected_status
    if expected_status == 200:
        resp_data = resp.json()
        assert "product" in resp_data
        resp_product = resp_data["product"]
        assert resp_product["name"] == new_product.name
        assert resp_product["description"] == new_product.description
        assert resp_product["regular_price"] == str(new_product.regular_price)
        assert resp_product["discount"] == new_product.discount
        assert (
            int(base64.b64decode(resp_product["category"]["id"]).decode())
            == new_product.category_id
        )
        assert (
            int(base64.b64decode(resp_product["platform"]["id"]).decode())
            == new_product.platform_id
        )
        assert (
            int(base64.b64decode(resp_product["delivery_method"]["id"]).decode())
            == new_product.delivery_method_id
        )
