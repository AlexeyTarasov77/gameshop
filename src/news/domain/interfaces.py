from types import EllipsisType
import typing as t
from core.pagination import PaginationParams, PaginationResT
from news import schemas
from news.models import News


class NewsRepositoryI(t.Protocol):
    async def create_with_image(
        self, dto: schemas.CreateNewsDTO, photo_url: str | None
    ) -> News: ...

    async def update_by_id(
        self,
        news_id: int,
        dto: schemas.UpdateNewsDTO,
        photo_url: str | None | EllipsisType,
    ) -> News: ...

    async def delete_by_id(self, news_id: int) -> None: ...

    async def paginated_list(
        self, pagination_params: PaginationParams
    ) -> PaginationResT[News]: ...

    async def get_by_id(self, news_id: int) -> News: ...
