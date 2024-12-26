from core.pagination import PaginationParams
from core.service import BaseService
from news.schemas import CreateNewsDTO, ShowNews, UpdateNewsDTO
from gateways.db.exceptions import DatabaseError


class NewsService(BaseService):
    async def list_news(
        self, pagination_params: PaginationParams
    ) -> tuple[list[ShowNews], int]:
        try:
            async with self.uow as uow:
                repo = uow.news_repo
                news = await repo.paginated_list(
                    limit=pagination_params.page_size,
                    offset=pagination_params.page_size
                    * (pagination_params.page_num - 1),
                )
                total_records = await repo.get_records_count()
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return [ShowNews.model_validate(el) for el in news], total_records

    async def create_news(self, dto: CreateNewsDTO) -> ShowNews:
        try:
            async with self.uow as uow:
                news = await uow.news_repo.create(dto)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return ShowNews.model_validate(news)

    async def get_news(self, news_id: int) -> ShowNews:
        try:
            async with self.uow as uow:
                news = await uow.news_repo.get_by_id(news_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return ShowNews.model_validate(news)

    async def update_news(self, dto: UpdateNewsDTO, news_id: int) -> ShowNews:
        try:
            async with self.uow as uow:
                news = await uow.news_repo.update_by_id(dto, news_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return ShowNews.model_validate(news)

    async def delete_news(self, news_id: int) -> None:
        try:
            async with self.uow as uow:
                await uow.news_repo.delete_by_id(news_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
