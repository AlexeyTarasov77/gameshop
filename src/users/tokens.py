import typing as t
from datetime import datetime, timedelta

import jwt


class JwtTokenProvider:
    def __init__(self, secret_key: str, signing_alg: str) -> None:
        self.secret = secret_key
        self.alg = signing_alg

    def new_token(self, payload: dict[str, t.Any], expires_in: timedelta) -> str:
        payload["exp"] = datetime.now() + expires_in
        return jwt.encode(payload, self.secret, self.alg)

    def extract_payload(self, token: str) -> dict[str, t.Any]:
        return jwt.decode(token, self.secret, [self.alg])
