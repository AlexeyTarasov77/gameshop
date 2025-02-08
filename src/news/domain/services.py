from core.pagination import PaginationParams
from core.services.base import BaseService
from core.services.exceptions import EntityNotFoundError
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
            news = await uow.news_repo.create_and_save_upload(dto)
        return ShowNews.model_validate(news)

    async def get_news(self, news_id: int) -> ShowNews:
        try:
            async with self._uow as uow:
                news = await uow.news_repo.get_by_id(news_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=news_id)
        return ShowNews.model_validate(news)

    async def update_news(self, dto: UpdateNewsDTO, news_id: int) -> ShowNews:
        try:
            async with self._uow as uow:
                news = await uow.news_repo.update_by_id(dto, news_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=news_id)
        return ShowNews.model_validate(news)

    async def delete_news(self, news_id: int) -> None:
        try:
            async with self._uow as uow:
                await uow.news_repo.delete_by_id(news_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=news_id)
