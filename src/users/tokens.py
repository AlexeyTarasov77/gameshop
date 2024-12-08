import typing as t
from datetime import datetime, timedelta

import jwt


class JwtTokenProvider:
    def __init__(self, secret_key: str, encryption_alg: str) -> None:
        self.secret = secret_key
        self.alg = encryption_alg

    def new_token(self, payload: dict[str, t.Any], expires_in: timedelta) -> str:
        return jwt.encode(payload, self.secret, self.alg, {"exp": datetime.now() + expires_in})
