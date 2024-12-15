from contextlib import nullcontext as does_not_raise
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest

from users.tokens import JwtTokenProvider


@pytest.fixture
def token_provider():
    jwt_token_provider = JwtTokenProvider("testsecret", "HS265")
    return jwt_token_provider


class TestJwtTokenProvider:
    @pytest.mark.parametrize(
        ["payload", "expires_in", "expected"],
        [
            ({"arg1": 1}, timedelta(), pytest.raises(ValueError)),
            ({"arg1": 1}, timedelta(days=1), does_not_raise()),
            ({}, timedelta(days=1), does_not_raise()),
        ],
    )
    def test_new_token(
        self, token_provider: JwtTokenProvider, payload: dict[str, Any], expires_in: timedelta, expected
    ):
        with patch("jwt.encode") as mock:
            mock_token = "mytoken"
            mock.return_value = mock_token
            with expected:
                token = token_provider.new_token(payload, expires_in)
            if expected is does_not_raise():
                assert token == mock_token
                mock.assert_called_once_with(
                    {**payload, "exp": datetime.now() + expires_in},
                    token_provider._secret,
                    token_provider.alg,
                )

    def test_extract_payload(self, token_provider: JwtTokenProvider):
        with patch("jwt.decode") as mock:
            test_payload = {"arg1": 1, "arg2": 2}
            test_token = "dsfasdjfsdafasgsda"
            mock.return_value = test_payload
            assert token_provider.extract_payload(test_token) == test_payload
            mock.assert_called_once_with(test_token, token_provider._secret, [token_provider.alg])
