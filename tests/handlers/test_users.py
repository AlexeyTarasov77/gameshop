import asyncio
from helpers import base64_to_int, is_base64
import typing as t
from contextlib import suppress
from datetime import datetime, timedelta

import pytest
from gateways.db.exceptions import NotFoundError
from gateways.db.repository import SqlAlchemyRepository
from users.domain.interfaces import TokenProviderI
from users.handlers import router
from users.models import User

from handlers.conftest import client, container, db, fake


def _gen_user_data() -> dict[str, str]:
    return {
        "email": fake.email(),
        "password": fake.password(length=10),
        "photo_url": fake.image_url(),
    }


@pytest.fixture
def new_user():
    data = _gen_user_data()
    data["password_hash"] = data.pop("password").encode()
    session = db.session_factory()
    repo = SqlAlchemyRepository(session)
    repo.model = User
    with asyncio.Runner() as runner:
        try:
            user: User = runner.run(repo.create(**data))
            runner.run(session.commit())
            yield user
            with suppress(NotFoundError):
                runner.run(repo.delete(id=user.id))
        finally:
            runner.run(session.close())


token_provider = t.cast(TokenProviderI, container.resolve(TokenProviderI))


@pytest.mark.parametrize(
    ["token_generator", "expected_status"],
    [
        (
            lambda user_id: token_provider.new_token(
                {"uid": user_id}, timedelta(days=1)
            ),
            200,
        ),
        (lambda user_id: "invalid", 422),
        (
            lambda user_id: token_provider.new_token({"fail": True}, timedelta(days=1)),
            400,
        ),
        (
            lambda user_id: token_provider.new_token(
                {"uid": user_id}, timedelta(days=-1)
            ),
            400,
        ),
        (lambda user_id: token_provider.new_token({"uid": 0}, timedelta(days=1)), 400),
        (
            lambda user_id: token_provider.new_token({"uid": 9999}, timedelta(days=1)),
            404,
        ),
    ],
)
def test_activate_user(
    new_user: User, token_generator: t.Callable[[int], str], expected_status: int
):
    resp = client.patch(
        f"{router.prefix}/activate", json={"token": token_generator(new_user.id)}
    )
    resp_data = resp.json()
    assert resp.status_code == expected_status
    if expected_status == 200:
        assert resp_data
        assert resp_data["activated"] is True
        assert resp_data["user"].pop("is_active") is True
        for resp_key, resp_value in resp_data["user"].items():
            user_value = getattr(new_user, resp_key)
            if type(user_value) is datetime:
                user_value = user_value.isoformat()
            if resp_key.endswith("id"):
                assert is_base64(resp_value)
                resp_value = base64_to_int(resp_value)
            assert resp_value == user_value


user_data = _gen_user_data()


@pytest.mark.parametrize(
    ["data", "expected_status"],
    [
        (user_data, 201),
        (user_data, 409),
        ({**_gen_user_data(), "email": "invalid"}, 422),
        ({**_gen_user_data(), "password": "short"}, 422),
        ({**_gen_user_data(), "photo_url": "invalid"}, 422),
    ],
)
def test_signup(data: dict[str, str], expected_status: int):
    resp = client.post(f"{router.prefix}/signup", json=data)
    assert resp.status_code == expected_status
    if expected_status == 201:
        resp_data = resp.json()
        assert data["email"] == resp_data["email"]
        assert data["photo_url"] == resp_data["photo_url"]
        assert resp_data["is_active"] is False
