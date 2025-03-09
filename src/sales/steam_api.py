from httpx import AsyncClient

from core.utils import JWTAuth
from sales.schemas import ExchangeRatesMappingDTO


class SteamAPIClientImpl:
    def __init__(
        self,
        client: AsyncClient,
        steam_api_auth_email: str,
        steam_api_auth_password: str,
    ):
        self._base_url = "https://api.ns.gifts/api/v1"
        self._client = client
        self._auth = JWTAuth(
            self._base_url + "/get_token",
            {"email": steam_api_auth_email, "password": steam_api_auth_password},
        )

    async def get_currency_rates(self) -> ExchangeRatesMappingDTO:
        resp = await self._client.post(
            self._base_url + "/steam/get_currency_rate", auth=self._auth
        )
        data = resp.json()
        data.pop("date")
        return ExchangeRatesMappingDTO.model_validate(data)
