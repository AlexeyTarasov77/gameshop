from core.utils import UnspecifiedType
from gateways.db.sqlalchemy_gateway import PaginationRepository
from news.models import News
from news.schemas import UpdateNewsDTO, CreateNewsDTO


class NewsRepository(PaginationRepository[News]):
    model = News

    async def update_by_id(
        self, news_id: int, dto: UpdateNewsDTO, photo_url: str | None | UnspecifiedType
    ) -> News:
        data = dto.model_dump(exclude={"photo"}, exclude_unset=True)
        if photo_url is not Ellipsis:
            data["photo_url"] = photo_url
        return await super().update(data, id=news_id)

    async def delete_by_id(self, news_id: int) -> None:
        await super().delete_or_raise_not_found(id=news_id)

    async def get_by_id(self, news_id: int) -> News:
        return await super().get_one(id=news_id)

    async def create_with_image(self, dto: CreateNewsDTO, photo_url: str | None):
        data = dto.model_dump(exclude={"photo"})
        return await super().create(**data, photo_url=photo_url)
