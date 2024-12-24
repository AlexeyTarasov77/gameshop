import asyncio
import typing as t
from contextlib import suppress

import pytest
from handlers.conftest import client, db, fake

from gateways.db.exceptions import NotFoundError
from gateways.db.repository import SqlAlchemyRepository
from news.handlers import router
from news.models import News
from helpers import check_paginated_response, is_base64


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
