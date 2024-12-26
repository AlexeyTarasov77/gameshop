import asyncio
from datetime import datetime
from itertools import zip_longest
import typing as t
from contextlib import suppress

import pytest
from handlers.conftest import client, db, fake

from gateways.db.exceptions import NotFoundError
from gateways.db.repository import SqlAlchemyRepository
from news.handlers import router
from news.models import News
from helpers import base64_to_int, check_paginated_response, is_base64


def _gen_news_data() -> dict[str, str]:
    return {
        "title": fake.sentence(),
        "description": fake.sentence(),
        "photo_url": fake.url(),
    }


@pytest.fixture
def new_news():
    session = db.session_factory()
    repo = SqlAlchemyRepository(session)
    repo.model = News
    with asyncio.Runner() as runner:
        try:
            news = runner.run(repo.create(**_gen_news_data()))
            runner.run(session.commit())
            yield news
            with suppress(NotFoundError):
                runner.run(repo.delete(id=news.id))
                runner.run(session.commit())
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
        session = db.session_factory()
        repo = SqlAlchemyRepository(session)
        repo.model = News
        with asyncio.Runner() as runner:
            try:
                created_news = runner.run(repo.get_one(**data))
            finally:
                runner.run(session.close())
        assert created_news
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
