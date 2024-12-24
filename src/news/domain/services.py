from core.pagination import PaginationParams
from core.service import BaseService
import typing as t
from news.schemas import ShowNews
from news.domain.interfaces import NewsRepositoryI
from gateways.db.exceptions import DatabaseError


class NewsService(BaseService):
    async def list_news(
        self, pagination_params: PaginationParams
    ) -> tuple[list[ShowNews], int]:
        try:
            async with self.uow as uow:
                repo = t.cast(NewsRepositoryI, uow.news_repo)
                news = await repo.paginated_list(
                    limit=pagination_params.page_size,
                    offset=pagination_params.page_size
                    * (pagination_params.page_num - 1),
                )
                total_records = await repo.get_records_count()
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return [ShowNews.model_validate(el) for el in news], total_records
