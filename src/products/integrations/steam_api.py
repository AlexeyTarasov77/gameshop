from collections.abc import Sequence
from httpx import AsyncClient
from core.utils import JWTAuth
from products.domain.services import ProductsService
from products.schemas import ExchangeRatesMappingDTO, SteamItemDTO


class GamesForFarmAPIClient:
    def __init__(self, client: AsyncClient, products_service: ProductsService) -> None:
        self._url = "https://gamesforfarm.com/api?key=GamesInStock_Gamesforfarm"
        self._client = client
        self._service = products_service

    def _good_to_dto(self, good: dict) -> SteamItemDTO:
        return SteamItemDTO.model_validate(
            {
                **good,
                "price_rub": good["price_wmr"],  # price in rubs
                "discount": 0,
                "image_url": good["icon"],
            }
        )

    async def _fetch_goods_without_bundle(self) -> Sequence[SteamItemDTO]:
        resp = await self._client.get(self._url)
        data = resp.json()["goods"]
        goods = list(data.values())
        goods_no_bundle = [
            good for good in goods if "bundle" not in good["name"].lower()
        ]
        return [self._good_to_dto(good) for good in goods_no_bundle]

    async def fetch_and_save(self):
        goods = await self._fetch_goods_without_bundle()
        await self._service.load_new_steam_items(goods)


class NSGiftsAPIClient:
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
