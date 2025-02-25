from typing import cast
from core.pagination import PaginationParams
from types import EllipsisType
from core.services.base import BaseService
from core.services.exceptions import EntityNotFoundError
from core.utils import save_upload_file
from gateways.db.exceptions import NotFoundError
from news.schemas import CreateNewsDTO, ShowNews, UpdateNewsDTO


class NewsService(BaseService):
    entity_name = "News"

    async def list_news(
        self, pagination_params: PaginationParams
    ) -> tuple[list[ShowNews], int]:
        async with self._uow as uow:
            news, total_records = await uow.news_repo.paginated_list(pagination_params)
        return [ShowNews.model_validate(el) for el in news], total_records

    async def create_news(self, dto: CreateNewsDTO) -> ShowNews:
        async with self._uow as uow:
            news = await uow.news_repo.create_with_image(
                dto, cast(str | None, dto.photo)
            )
        return ShowNews.model_validate(news)

    async def get_news(self, news_id: int) -> ShowNews:
        try:
            async with self._uow as uow:
                news = await uow.news_repo.get_by_id(news_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=news_id)
        return ShowNews.model_validate(news)

    async def update_news(self, news_id: int, dto: UpdateNewsDTO) -> ShowNews:
        photo_url: EllipsisType | str | None = ...
        if "photo" in dto.model_fields_set:  # if none is set explicitly
            photo_url = cast(str | None, dto.photo)
        try:
            async with self._uow as uow:
                news = await uow.news_repo.update_by_id(news_id, dto, photo_url)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=news_id)
        return ShowNews.model_validate(news)

    async def delete_news(self, news_id: int) -> None:
        try:
            async with self._uow as uow:
                await uow.news_repo.delete_by_id(news_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=news_id)
