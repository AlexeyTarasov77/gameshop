from http import HTTPStatus
import typing as t

from fastapi import APIRouter

from core.http.exceptions import HttpExceptionsMapper
from core.ioc import Inject
from core.pagination import PaginatedResponse, PaginationDep
from core.service import ServiceError
from news.domain.services import NewsService
from news.schemas import CreateNewsDTO, ShowNews

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


@router.post("/create", status_code=HTTPStatus.CREATED)
async def create_news(dto: CreateNewsDTO, news_service: NewsServiceDep) -> ShowNews:
    print("got req", dto)
    try:
        news = await news_service.create_news(dto)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    print("returning news")
    return news
