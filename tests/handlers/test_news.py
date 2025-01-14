from datetime import datetime
from itertools import zip_longest

import pytest
from handlers.helpers import (
    base64_to_int,
    check_paginated_response,
    pagination_test_cases,
    create_model_obj,
    get_model_obj,
    is_base64,
)

from handlers.conftest import client, fake
from news.handlers import router
from news.models import News


def _gen_news_data() -> dict[str, str]:
    return {
        "title": fake.sentence(),
        "description": fake.sentence(),
        "photo_url": fake.url(),
    }


@pytest.fixture
def new_news():
    yield from create_model_obj(News, **_gen_news_data())


@pytest.mark.parametrize(
    ["expected_status", "params"],
    pagination_test_cases,
)
def test_list_news(expected_status: int, params: dict[str, int] | None):
    resp = client.get(f"{router.prefix}/", params=params)
    assert resp.status_code == expected_status
    resp_data = resp.json()
    if expected_status == 200:
        check_paginated_response("news", resp_data, params)


@pytest.mark.parametrize(
    ["expected_status", "data"],
    [(201, _gen_news_data()), (422, {**_gen_news_data(), "photo_url": "invalid"})],
)
def test_create_news(expected_status: int, data: dict[str, str]):
    resp = client.post(f"{router.prefix}/create", json=data)
    assert resp.status_code == expected_status
    resp_data = resp.json()
    if expected_status == 201:
        assert is_base64(resp_data["id"])
        for key, value in data.items():
            assert resp_data[key] == value
        created_news = get_model_obj(News, **data)
        assert created_news is not None
        for key, value in data.items():
            assert getattr(created_news, key) == value


@pytest.mark.parametrize(
    ["expected_status", "news_id"], [(200, None), (422, -1), (404, 999999)]
)
def test_get_news(new_news: News, expected_status: int, news_id: int | None):
    news_id = news_id or new_news.id
    resp = client.get(f"{router.prefix}/detail/{news_id}")
    assert resp.status_code == expected_status
    if expected_status == 200:
        resp_data = resp.json()
        assert resp_data
        assert is_base64(resp_data["id"])
        assert base64_to_int(resp_data["id"]) == new_news.id
        assert resp_data["title"] == new_news.title
        assert resp_data["description"] == new_news.description
        assert resp_data["created_at"] == new_news.created_at.isoformat()
        assert resp_data["updated_at"] == new_news.updated_at.isoformat()


@pytest.mark.parametrize(
    ["data", "expected_status", "news_id"],
    [
        (_gen_news_data(), 200, None),
        ({"title": fake.sentence()}, 200, None),
        ({}, 400, None),
        (_gen_news_data(), 404, 999999),
        (_gen_news_data(), 422, -1),
    ],
)
def test_update_news(
    new_news: News, data: dict[str, str], expected_status: int, news_id: int | None
):
    news_id = news_id or new_news.id
    resp = client.patch(f"{router.prefix}/update/{news_id}", json=data)
    assert resp.status_code == expected_status
    if expected_status == 200:
        resp_data = resp.json()
        assert is_base64(resp_data["id"])

        resp_data["id"] = base64_to_int(resp_data["id"])

        for resp_key, data_key in zip_longest(resp_data, data):
            if data_key is None:
                if resp_key in data:
                    continue
                news_val = getattr(new_news, resp_key)
                resp_val = resp_data[resp_key]
                if type(news_val) is datetime:
                    news_val = news_val.isoformat()
                else:
                    news_val = type(resp_val)(news_val)
                assert resp_val == news_val
            else:
                assert resp_data[data_key] == data[data_key]


@pytest.mark.parametrize(
    ["expected_status", "news_id"], [(204, None), (404, 999999), (422, -1)]
)
def test_delete_news(new_news: News, expected_status: int, news_id: int):
    news_id = news_id or new_news.id
    resp = client.delete(f"{router.prefix}/delete/{news_id}")
    assert resp.status_code == expected_status
    if expected_status == 204:
        assert get_model_obj(News, id=new_news.id) is None
