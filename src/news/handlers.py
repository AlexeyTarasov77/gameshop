from http import HTTPStatus
import typing as t

from fastapi import APIRouter, Depends, Form, HTTPException

from core.exception_mappers import HttpExceptionsMapper
from core.ioc import Inject
from core.schemas import EntityIDParam
from core.pagination import PaginatedResponse, PaginationDep
from core.services.exceptions import ServiceError
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
    try:
        news, total_records = await news_service.list_news(pagination_params)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return NewsPaginatedResponse(
        news=news,
        total_records=total_records,
        total_on_page=len(news),
        first_page=1,
        **pagination_params.model_dump(),
    )


@router.post(
    "/create", status_code=HTTPStatus.CREATED, dependencies=[Depends(require_admin)]
)
async def create_news(
    dto: t.Annotated[CreateNewsDTO, Form()], news_service: NewsServiceDep
) -> ShowNews:
    try:
        news = await news_service.create_news(dto)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return news


@router.get("/detail/{news_id}")
async def get_news(news_id: EntityIDParam, news_service: NewsServiceDep) -> ShowNews:
    try:
        news = await news_service.get_news(int(news_id))
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return news


@router.patch("/update/{news_id}", dependencies=[Depends(require_admin)])
async def update_news(
    news_id: EntityIDParam,
    dto: t.Annotated[UpdateNewsDTO, Form()],
    news_service: NewsServiceDep,
) -> ShowNews:
    if not dto.model_dump(exclude_unset=True):
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, detail="Nothing to update. No data provided"
        )
    try:
        news = await news_service.update_news(dto, int(news_id))
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return news


@router.delete(
    "/delete/{news_id}",
    status_code=HTTPStatus.NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_news(news_id: EntityIDParam, news_service: NewsServiceDep):
    try:
        await news_service.delete_news(int(news_id))
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
