from httpx import AsyncClient
from core.pagination import PaginationParams, PaginationResT
from products.schemas import ProductFromAPIDTO


class GamesForFarmAPIClient:
    def __init__(self, client: AsyncClient) -> None:
        self._url = "https://gamesforfarm.com/api?key=GamesInStock_Gamesforfarm"
        self._client = client

    async def get_paginated(
        self, pagination_params: PaginationParams
    ) -> PaginationResT[ProductFromAPIDTO]:
        resp = await self._client.get(self._url)
        data: dict = resp.json()["goods"]
        goods = list(data.values())
        total = len(goods)
        filtered = [item for item in goods if "bundle" not in item["name"].lower()]
        offset = pagination_params.calc_offset()
        paginated_items = filtered[offset : offset + pagination_params.page_size]
        return [
            ProductFromAPIDTO(
                id=item["id"],
                name=item["name"],
                description=item["description"],
                image_url=item["icon"],
                price_rub=item["price_wmr"],
            )
            for item in paginated_items
        ], total
