from sqlalchemy import insert, update
from core.ioc import Resolve
from handlers.helpers import base64_to_int, create_model_obj, is_base64
import typing as t
from datetime import datetime, timedelta

import pytest
from users.domain.interfaces import (
    PasswordHasherI,
    StatefullTokenProviderI,
    StatelessTokenProviderI,
)
from users.handlers import router
from users.models import Token, User

from handlers.conftest import client, fake, db

statefull_token_provider = Resolve(StatefullTokenProviderI)


def _gen_user_data() -> dict[str, str]:
    return {
        "username": fake.user_name(),
        "email": fake.email(),
        "password": fake.password(length=10),
        "photo_url": fake.image_url(),
    }


@pytest.fixture
def new_user():
    data = _gen_user_data()
    hasher = Resolve(PasswordHasherI)
    hashed_password = hasher.hash(data.pop("password"))
    yield from create_model_obj(User, password_hash=hashed_password, **data)


@pytest.mark.parametrize(
    ["token_generator", "expected_status"],
    [
        (
            lambda gen_token: gen_token(None),
            200,
        ),
        (lambda gen_token: "123456789", 422),
        (lambda gen_token: gen_token(9999999), 404),
        (lambda gen_token: "Drmhze6EPcv0fN_81Bj-nA", 404),
    ],
)
def test_activate_user(
    new_user: User,
    token_generator: t.Callable[[t.Callable[[int | None], str]], str],
    expected_status: int,
):
    def gen_token(user_id: int | None) -> str:
        plain_token, token_obj = statefull_token_provider.new_token(
            user_id or new_user.id, timedelta(days=1)
        )
        if user_id is None:
            # insert only in case if user_id is taken from real user due to db integrity error otherwise
            with db.sync_engine.begin() as conn:
                conn.execute(insert(Token).values(**token_obj.dump()))
        return plain_token

    plain_token = token_generator(gen_token)
    resp = client.patch(f"{router.prefix}/activate", json={"token": plain_token})
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


@pytest.mark.parametrize(
    ["expected_status", "email", "password", "is_user_active"],
    [
        (200, None, None, True),
        (403, None, None, False),
        (401, None, "incorrect", True),
        (401, "notfound_email@foo.com", None, True),
        (422, "invalid", None, True),
    ],
)
def test_signin(
    expected_status: int,
    email: str | None,
    password: str | None,
    is_user_active: bool,
):
    with db.sync_engine.begin() as conn:
        hasher = Resolve(PasswordHasherI)
        user_password = fake.password(length=10)
        hashed_password = hasher.hash(user_password)
        stmt = (
            insert(User)
            .values(
                password_hash=hashed_password,
                is_active=is_user_active,
                email=fake.email(),
                username=fake.user_name(),
            )
            .returning(User)
        )
        user = conn.execute(stmt).one()
    email = email or user.email
    password = password or user_password
    resp = client.post(
        f"{router.prefix}/signin", json={"email": email, "password": password}
    )
    resp_data = resp.json()
    assert resp.status_code == expected_status
    if expected_status == 200:
        assert resp_data.get("token")


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
        for k, v in resp_data.items():
            if k in data:
                assert data[k] == v
        assert resp_data["is_active"] is False


@pytest.mark.parametrize(
    ["email", "expected_status", "is_user_active"],
    [
        (None, 202, False),
        ("invalid", 422, False),
        ("notfound@notfound.com", 404, False),
        (None, 400, True),
    ],
)
def test_resend_activation_token(
    new_user: User, email: str | None, expected_status: int, is_user_active: bool
):
    email = email or new_user.email
    if is_user_active:
        with db.sync_engine.begin() as conn:
            conn.execute(update(User).filter_by(id=new_user.id).values(is_active=True))
    resp = client.post(
        f"{router.prefix}/resend-activation-token", json={"email": email}
    )
    assert resp.status_code == expected_status
