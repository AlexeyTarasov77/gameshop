import typing as t
from core.pagination import PaginationParams
from news import schemas
from news.models import News


class NewsRepositoryI(t.Protocol):
    async def create_and_save_upload(self, dto: schemas.CreateNewsDTO) -> News: ...

    async def update_by_id(self, dto: schemas.UpdateNewsDTO, news_id: int) -> News: ...

    async def delete_by_id(self, news_id: int) -> None: ...

    async def paginated_list(
        self, pagination_params: PaginationParams
    ) -> t.Sequence[News]: ...

    async def get_records_count(self) -> int: ...

    async def get_by_id(self, news_id: int) -> News: ...
