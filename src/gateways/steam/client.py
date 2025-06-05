from collections.abc import Sequence
from decimal import Decimal
from core.logging import AbstractLogger
import uuid
from httpx import AsyncClient
from core.utils import JWTAuth
from core.utils.httpx_utils import log_request, log_response
from orders.schemas import CreateSteamGiftOrderDTO, CreateSteamTopUpOrderDTO
from products.domain.services import ProductsService
from products.schemas import SteamGameParsedDTO
from gateways.currency_converter import ExchangeRatesMappingDTO


class GamesForFarmAPIClient:
    def __init__(
        self,
        client: AsyncClient,
        products_service: ProductsService,
        logger: AbstractLogger,
    ) -> None:
        self._url = "https://gamesforfarm.com/api?key=GamesInStock_Gamesforfarm"
        self._client = client
        self._service = products_service
        self._logger = logger

    def _good_to_dto(self, good: dict) -> SteamGameParsedDTO:
        return SteamGameParsedDTO.model_validate(
            {
                **good,
                "price_rub": good["price_wmr"],  # price in rubs
                "discount": 0,
                "image_url": good["icon"],
            }
        )

    async def _fetch_goods_without_bundle(self) -> Sequence[SteamGameParsedDTO]:
        self._logger.info("Fetching goods from api...")
        resp = await self._client.get(self._url)
        data = resp.json()["goods"]
        goods = list(data.values())
        goods_no_bundle = [
            good for good in goods if "bundle" not in good["name"].lower()
        ]
        self._logger.info("Goods succesfully fetched and filtered")
        return [self._good_to_dto(good) for good in goods_no_bundle]

    # async def fetch_and_save(self):
    #     goods = await self._fetch_goods_without_bundle()
    #     await self._service.load_new_steam_items(goods)
    #     self._logger.info("Fetched goods succesfully loaded")


class NSGiftsAPIClient:
    def __init__(
        self,
        client: AsyncClient,
        logger: AbstractLogger,
        steam_api_auth_email: str,
        steam_api_auth_password: str,
    ):
        self._base_url = "https://api.ns.gifts/api/v1"
        self._client = client
        self._logger = logger
        self._auth = JWTAuth(
            self._base_url + "/get_token",
            {"email": steam_api_auth_email, "password": steam_api_auth_password},
        )

    def _get_logging_prefix(self, func_name: str) -> str:
        return self.__class__.__name__ + "." + func_name

    async def get_currency_rates(self) -> ExchangeRatesMappingDTO:
        with log_request(self._get_logging_prefix("get_currency_rates"), self._logger):
            resp = await self._client.post(
                self._base_url + "/steam/get_currency_rate", auth=self._auth
            )
            log_response(resp, self._logger)
            resp.raise_for_status()
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
        log_response(resp, self._logger)
        resp.raise_for_status()
        data = resp.json()
        return Decimal(data["usd_price"]), float(data["exchange_rate"])

    async def create_top_up_order(self, dto: CreateSteamTopUpOrderDTO) -> uuid.UUID:
        service_id = 1  # id for steam top-up service
        usd_min_deposit = 0.13
        with log_request(self._get_logging_prefix("create_top_up_order"), self._logger):
            usd_amount, exchange_rate = await self._convert_amount_to_usd(
                dto.rub_amount
            )
        if usd_amount < usd_min_deposit:
            raise ValueError(
                "deposit should be >= %s" % (usd_min_deposit * exchange_rate)
            )
        top_up_id = uuid.uuid4()
        with log_request(self._get_logging_prefix("create_top_up_order"), self._logger):
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
            log_response(resp, self._logger)
            resp.raise_for_status()
        return top_up_id

    async def top_up_complete(self, top_up_id: uuid.UUID):
        with log_request(self._get_logging_prefix("top_up_complete"), self._logger):
            resp = await self._client.post(
                self._base_url + "/pay_order",
                json={"custom_id": str(top_up_id)},
                auth=self._auth,
            )
            log_response(resp, self._logger)
            resp.raise_for_status()

    async def create_gift_order(
        self, dto: CreateSteamGiftOrderDTO, sub_id: int
    ) -> uuid.UUID:
        self._logger.info(
            "Creating steam gift order", sub_id=sub_id, dto=dto.model_dump()
        )
        with log_request(self._get_logging_prefix("create_gift_order"), self._logger):
            resp = await self._client.post(
                self._base_url + "/steam_gift/create_order",
                json={
                    "sub_id": sub_id,
                    "friendLink": dto.friend_link,
                    "region": dto.region,
                },
                auth=self._auth,
            )
            log_response(resp, self._logger)
            resp.raise_for_status()
        data = resp.json()
        return uuid.UUID(data["custom_id"])

    async def pay_gift_order(self, order_id: uuid.UUID):
        self._logger.info("Paying gift order", order_id=order_id)
        with log_request(self._get_logging_prefix("pay_gift_order"), self._logger):
            resp = await self._client.post(
                self._base_url + "/steam_gift/pay_order",
                json={"custom_id": str(order_id)},
                auth=self._auth,
                timeout=None,
            )
            log_response(resp, self._logger)
            resp.raise_for_status()
