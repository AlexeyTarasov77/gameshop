import httpx
from typing import Any


class JWTAuth(httpx.Auth):
    requires_response_body = True

    def __init__(
        self,
        auth_url: str,
        credentials: dict[str, Any],
        resp_token_key: str = "access_token",
    ):
        self._token: str | None = None
        self._auth_url = auth_url
        self._credentials = credentials
        self._resp_token_key = resp_token_key

    def auth_flow(self, request: httpx.Request):
        self._set_auth_header(request)
        if self._token is None:
            self.authenticate(request)
        response = yield request
        if response.status_code in (401, 403):
            # If the server issues a 401 response then resend the request,
            yield from self.authenticate(request)
            yield request

    def authenticate(self, request: httpx.Request):
        response: httpx.Response = yield httpx.Request(
            "POST", self._auth_url, json=self._credentials
        )
        self._token = response.json()[self._resp_token_key]
        self._set_auth_header(request)

    def _set_auth_header(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self._token}"
