import typing as t
from secrets import token_urlsafe
from datetime import datetime, timedelta

import jwt

from users.domain.interfaces import TokenHasherI
from users.models import Token


def _get_expiry(expires_in: timedelta) -> datetime:
    if expires_in.total_seconds() == 0:
        raise ValueError("Invalid expiration")
    return datetime.now() + expires_in


class JwtTokenProvider:
    def __init__(self, secret_key: str, signing_alg: str) -> None:
        self._secret = secret_key
        self.alg = signing_alg

    def new_token(self, payload: dict[str, t.Any], expires_in: timedelta) -> str:
        payload["exp"] = _get_expiry(expires_in)
        return jwt.encode(payload, self._secret, self.alg)

    def extract_payload(self, token: str) -> dict[str, t.Any]:
        return jwt.decode(token, self._secret, [self.alg])


class SecureTokenProvider:
    def __init__(self, hasher: TokenHasherI):
        self.hasher = hasher

    def new_token(self, user_id: int, expires_in: timedelta) -> tuple[str, Token]:
        expiry = _get_expiry(expires_in)
        plain_token = token_urlsafe(16)
        return plain_token, Token(
            hash=self.hasher.hash(plain_token), user_id=user_id, expiry=expiry
        )
