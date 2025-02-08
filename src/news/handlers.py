from http import HTTPStatus
import typing as t

from fastapi import APIRouter, Depends, Form

from core.ioc import Inject
from core.schemas import EntityIDParam, check_dto_not_empty
from core.pagination import PaginatedResponse
from core.dependencies import PaginationDep, restrict_content_type
from news.domain.services import NewsService
from news.schemas import CreateNewsDTO, ShowNews, UpdateNewsDTO
from users.dependencies import require_admin

router = APIRouter(prefix="/news", tags=["news"])

NewsServiceDep = t.Annotated[NewsService, Inject(NewsService)]


class NewsPaginatedResponse(PaginatedResponse):
    news: list[ShowNews]


@router.get("/")
async def list_news(
    pagination_params: PaginationDep, news_service: NewsServiceDep
) -> NewsPaginatedResponse:
    news, total_records = await news_service.list_news(pagination_params)
    return NewsPaginatedResponse(
        news=news,
        total_records=total_records,
        total_on_page=len(news),
        first_page=1,
        **pagination_params.model_dump(),
    )


@router.post(
    "/create",
    status_code=HTTPStatus.CREATED,
    dependencies=[
        restrict_content_type("multipart/form-data"),
        Depends(require_admin),
    ],
)
async def create_news(
    dto: t.Annotated[CreateNewsDTO, Form(media_type="multipart/form-data")],
    news_service: NewsServiceDep,
) -> ShowNews:
    return await news_service.create_news(dto)


@router.get("/detail/{news_id}")
async def get_news(news_id: EntityIDParam, news_service: NewsServiceDep) -> ShowNews:
    return await news_service.get_news(int(news_id))


@router.patch(
    "/update/{news_id}",
    dependencies=[
        restrict_content_type("multipart/form-data"),
        Depends(require_admin),
    ],
)
async def update_news(
    news_id: EntityIDParam,
    dto: t.Annotated[UpdateNewsDTO, Form(media_type="multipart/form-data")],
    news_service: NewsServiceDep,
) -> ShowNews:
    check_dto_not_empty(dto)
    return await news_service.update_news(dto, int(news_id))


@router.delete(
    "/delete/{news_id}",
    status_code=HTTPStatus.NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_news(news_id: EntityIDParam, news_service: NewsServiceDep):
    await news_service.delete_news(int(news_id))
