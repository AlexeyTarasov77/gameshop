from gateways.db.repository import PaginationRepository
from news.models import News
from news.schemas import UpdateNewsDTO, CreateNewsDTO


class NewsRepository(PaginationRepository[News]):
    model = News

    async def update_by_id(self, dto: UpdateNewsDTO, news_id: int) -> News:
        return await super().update(dto.model_dump(exclude_unset=True), id=news_id)

    async def delete_by_id(self, news_id: int) -> None:
        await super().delete(id=news_id)

    async def get_by_id(self, news_id: int) -> News:
        return await super().get_one(id=news_id)

    async def create(self, dto: CreateNewsDTO):
        return await super().create(**dto.model_dump())
