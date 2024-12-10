import random
import typing as t
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from products.handlers import router
from products.models import Product

from handlers.conftest import client, faker


def _gen_create_product_data():
    return {
        "name": faker.name(),
        "description": faker.sentence(),
        "regular_price": str(Decimal(faker.random_number(4))),
        "image_url": faker.image_url(),
        "delivery_method": random.choice(Product.DELIVERY_METHODS_CHOICES),
        "discount": random.randint(0, 100),
        "discount_valid_to": str(faker.date_time_between(datetime.now(), timedelta(days=30))),
        "category": {"id": random.randint(1, 3), "name": faker.company()},
        "platform": {"id": random.randint(1, 3), "name": faker.street_name()},
    }


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
        assert resp_data["regular_price"] == data["regular_price"]
        assert resp_data["discount"] == data["discount"]
        assert resp_data["category_id"] == data["category"]["id"]
        assert resp_data["platform_id"] == data["platform"]["id"]
