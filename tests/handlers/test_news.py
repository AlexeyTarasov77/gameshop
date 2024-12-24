import asyncio
import typing as t
from contextlib import suppress

import pytest
from handlers.conftest import client, db, fake

from gateways.db.exceptions import NotFoundError
from gateways.db.repository import SqlAlchemyRepository
from news.handlers import router
from news.models import News
from helpers import check_paginated_response


def _gen_news_data() -> dict[str, t.Any]:
    return {
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
