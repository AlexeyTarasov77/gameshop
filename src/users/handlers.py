import typing as t
from http import HTTPStatus

from core.http.exceptions import HttpExceptionsMapper
from core.ioc import Inject
from core.service import ServiceError
from fastapi import APIRouter

from users.domain.services import UsersService
from users.schemas import CreateUserDTO, ShowUser

router = APIRouter(prefix="/users", tags=["users", "auth"])


@router.post("/signup", status_code=HTTPStatus.CREATED)
async def signup(
    dto: CreateUserDTO,
    users_service: t.Annotated[UsersService, Inject(UsersService)],
) -> ShowUser:
    try:
        return await users_service.signup(dto)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
