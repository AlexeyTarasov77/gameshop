import json
from hashlib import md5
from httpx import AsyncClient
from redis.asyncio import Redis
from core.pagination import PaginationParams, PaginationResT
from gateways.db.exceptions import NotFoundError
from products.schemas import ProductFromAPIDTO


class GamesForFarmAPIClient:
    def __init__(self, client: AsyncClient, redis: Redis) -> None:
        self._url = "https://gamesforfarm.com/api?key=GamesInStock_Gamesforfarm"
        self._client = client
        self._cache = redis
        self._cache_prefix = "cache:goods:"

    async def _fetch_goods_with_caching(self, *args, **kwargs) -> dict[str, dict]:
        cache_key = (
            self._cache_prefix
            + md5(str(args).encode() + str(kwargs).encode()).hexdigest()
        )
        cached_goods = await self._cache.get(cache_key)
        if cached_goods:
            return json.loads(cached_goods)["goods"]
        resp = await self._client.get(self._url)
        await self._cache.set(cache_key, resp.content, ex=60 * 5)
        return resp.json()["goods"]

    def _good_to_dto(self, good: dict) -> ProductFromAPIDTO:
        return ProductFromAPIDTO(
            id=good["id"],
            name=good["name"],
            description=good["description"],
            image_url=good["icon"],
            price_rub=good["price_wmr"],
        )

    async def get_paginated(
        self, pagination_params: PaginationParams
    ) -> PaginationResT[ProductFromAPIDTO]:
        data = await self._fetch_goods_with_caching(pagination_params)
        goods = list(data.values())
        total = len(goods)
        filtered = [good for good in goods if "bundle" not in good["name"].lower()]
        offset = pagination_params.calc_offset()
        paginated_goods = filtered[offset : offset + pagination_params.page_size]
        return [self._good_to_dto(good) for good in paginated_goods], total

    async def get_by_id(self, product_id: int) -> ProductFromAPIDTO:
        data = await self._fetch_goods_with_caching(product_id)
        good = data.get(str(product_id), None)
        if good is None:
            raise NotFoundError()
        return self._good_to_dto(good)
