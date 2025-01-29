from core.utils import save_upload_file
from gateways.db.repository import PaginationRepository
from news.models import News
from news.schemas import UpdateNewsDTO, CreateNewsDTO


class NewsRepository(PaginationRepository[News]):
    model = News

    async def update_by_id(self, dto: UpdateNewsDTO, news_id: int) -> News:
        data = dto.model_dump(exclude={"photo"}, exclude_unset=True)
        if dto.photo:
            data["photo_url"] = await save_upload_file(dto.photo)
        return await super().update(data, id=news_id)

    async def delete_by_id(self, news_id: int) -> None:
        await super().delete_or_raise_not_found(id=news_id)

    async def get_by_id(self, news_id: int) -> News:
        return await super().get_one(id=news_id)

    async def create_and_save_upload(self, dto: CreateNewsDTO):
        data = dto.model_dump(exclude={"photo"})
        if dto.photo:
            data["photo_url"] = await save_upload_file(dto.photo)
        return await super().create(**data)
