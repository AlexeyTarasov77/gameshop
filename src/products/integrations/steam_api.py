from collections.abc import Sequence
from decimal import Decimal
import uuid
from httpx import AsyncClient
from core.utils import JWTAuth
from orders.schemas import SteamTopUpCreateDTO
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

    async def _convert_amount_to_usd(
        self, rub_amount: Decimal
    ) -> tuple[Decimal, float]:
        resp = await self._client.post(
            self._base_url + "/steam/get_amount",
            json={"amount": str(rub_amount)},
            auth=self._auth,
        )
        data = resp.json()
        return Decimal(data["usd_price"]), float(data["exchange_rate"])

    async def create_top_up_request(self, dto: SteamTopUpCreateDTO) -> uuid.UUID:
        service_id = 1  # id for steam top-up service
        usd_amount, exchange_rate = await self._convert_amount_to_usd(dto.rub_amount)
        usd_min_deposit = 0.13
        if usd_amount < usd_min_deposit:
            raise ValueError(
                "amount_rub should be >= %s" % (usd_min_deposit * exchange_rate)
            )
        top_up_id = uuid.uuid4()
        resp = await self._client.post(
            self._base_url + "/create_order",
            json={
                "service_id": service_id,
                "custom_id": str(top_up_id),
                "quantity": str(usd_amount),
                "data": dto.steam_login,
            },
            auth=self._auth,
        )
        assert resp.json()["status"] == 1
        return top_up_id

    async def top_up_complete(self, top_up_id: uuid.UUID):
        resp = await self._client.post(
            "/pay_order", json={"custom_id": top_up_id}, auth=self._auth
        )
        data = resp.json()
        print(data)
