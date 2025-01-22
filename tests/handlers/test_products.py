import base64
import random
import typing as t
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import zip_longest

import pytest
from handlers.helpers import (
    check_paginated_response,
    pagination_test_cases,
    is_base64,
    base64_to_int,
    create_model_obj,
    get_model_obj,
)
from sqlalchemy import text

from handlers.conftest import client, db, fake
from products.handlers import router
from products.models import BaseRefModel, Category, DeliveryMethod, Platform, Product


def compare_product_fields(
    src: dict[str, t.Any], comparable: dict[str, t.Any] | Product
):
    def get_comparable_val(key: str):
        try:
            return comparable[key]  # type: ignore
        except TypeError:
            return getattr(comparable, key)

    assert src["name"] == get_comparable_val("name")
    assert src["description"] == get_comparable_val("description")
    assert src["regular_price"] == str(get_comparable_val("regular_price"))
    assert src["discount"] == get_comparable_val("discount")


def _gen_product_data(encode_ids: bool = True) -> dict[str, t.Any]:
    with db.sync_engine.begin() as conn:
        res = conn.execute(
            text(
                "SELECT c.id, p.id, dm.id FROM category c, platform p, delivery_method dm"
            )
        )

        relation_ids = random.choice(res.unique().all())
        if encode_ids:
            relation_ids = [
                base64.b64encode(str(n).encode()).decode() for n in relation_ids
            ]
        category_id, platform_id, delivery_method_id = relation_ids
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


def _new_ref_model_obj(obj_model: type[BaseRefModel]):
    return create_model_obj(obj_model, name=fake.name(), url=fake.url())


@pytest.fixture
def new_delivery_method():
    yield from _new_ref_model_obj(DeliveryMethod)


@pytest.fixture
def new_platform():
    yield from _new_ref_model_obj(Platform)


@pytest.fixture
def new_category():
    yield from _new_ref_model_obj(Category)


@pytest.fixture
def new_product():
    data = _gen_product_data(encode_ids=False)
    data["category_id"], data["platform_id"], data["delivery_method_id"] = (
        data.pop("category")["id"],
        data.pop("platform")["id"],
        data.pop("delivery_method")["id"],
    )
    yield from create_model_obj(Product, **data)


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
def test_create_product(
    new_category,
    new_platform,
    new_delivery_method,
    data: dict[str, t.Any],
    expected_status: int,
):
    resp = client.post(f"{router.prefix}/create", json=data)
    resp_data = resp.json()
    assert resp.status_code == expected_status
    if expected_status == 201:
        compare_product_fields(resp_data, data)
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
        assert all(
            [
                is_base64(resp_data["delivery_method_id"]),
                is_base64(resp_data["platform_id"]),
                is_base64(resp_data["category_id"]),
                is_base64(resp_data["id"]),
            ]
        )

        resp_data["id"] = base64_to_int(resp_data["id"])
        resp_data["category_id"] = base64_to_int(resp_data["category_id"])
        resp_data["platform_id"] = base64_to_int(resp_data["platform_id"])
        resp_data["delivery_method_id"] = base64_to_int(resp_data["delivery_method_id"])

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
    ["expected_status", "product_id"], [(204, None), (404, 999999), (422, -1)]
)
def test_delete_product(
    new_product: Product, expected_status: int, product_id: int | None
):
    product_id = product_id or new_product.id
    resp = client.delete(f"{router.prefix}/delete/{product_id}")
    assert resp.status_code == expected_status
    if expected_status == 204:
        assert get_model_obj(Product, id=new_product.id) is None


@pytest.mark.parametrize(["expected_status", "params"], pagination_test_cases)
def test_list_products(expected_status: int, params: dict[str, int] | None):
    resp = client.get(f"{router.prefix}/", params=params)
    assert resp.status_code == expected_status
    resp_data = resp.json()
    if expected_status == 200:
        check_paginated_response("products", resp_data, params)


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
        compare_product_fields(resp_product, new_product)
        assert resp_product["total_price"] == str(new_product.total_price)
        assert base64_to_int(resp_product["category"]["id"]) == new_product.category_id
        assert base64_to_int(resp_product["platform"]["id"]) == new_product.platform_id
        assert (
            base64_to_int(resp_product["delivery_method"]["id"])
            == new_product.delivery_method_id
        )


def _test_objects_list_helper(obj: Category | DeliveryMethod | Platform, url: str):
    resp = client.get(f"{router.prefix}/{url}")
    resp_key = url.replace("-", "_")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert len(resp_data[resp_key]) > 0
    assert all((is_base64(obj["id"]) for obj in resp_data[resp_key]))
    assert obj.id in [base64_to_int(resp_obj["id"]) for resp_obj in resp_data[resp_key]]
    resp_obj = next(
        (
            resp_obj
            for resp_obj in resp_data[resp_key]
            if base64_to_int(resp_obj["id"]) == obj.id
        )
    )
    assert resp_obj
    assert resp_obj["name"] == obj.name
    assert resp_obj["url"] == obj.url


def test_platforms_list(new_platform: Platform):
    _test_objects_list_helper(new_platform, "platforms")


def test_categories_list(new_category: Category):
    _test_objects_list_helper(new_category, "categories")


def test_delivery_methods_list(new_delivery_method: DeliveryMethod):
    _test_objects_list_helper(new_delivery_method, "delivery-methods")


@pytest.mark.parametrize(
    ["expected_status", "params"],
    [
        (200, {"query": "".join(fake.random_letters(2))}),
        (
            200,
            {"page_size": 5, "page_num": 1, "query": "".join(fake.random_letters(2))},
        ),
        (422, None),
        (422, {"query": ""}),
        (422, {"page_size": 0, "query": "".join(fake.random_letters(2))}),
        (422, {"page_num": 0, "query": "".join(fake.random_letters(2))}),
    ],
)
def test_search_products(expected_status: int, params: dict[str, int] | None):
    resp = client.get(f"{router.prefix}/search", params=params)
    assert resp.status_code == expected_status
    resp_data = resp.json()
    if expected_status == 200:
        assert params
        check_paginated_response("products", resp_data, params)
        for product in resp_data["products"]:
            assert params["query"] in product["name"]
