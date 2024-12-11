import typing as t
from http import HTTPStatus

from core.http.exceptions import HttpExceptionsMapper
from core.ioc import Inject
from core.service import ServiceError
from fastapi import APIRouter, Body, HTTPException

from users.domain.services import InvalidTokenServiceError, UsersService
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


@router.patch("/activate")
async def activate_user(
    token: t.Annotated[str, Body(min_length=50, embed=True)],
    users_service: t.Annotated[UsersService, Inject(UsersService)],
) -> dict[str, bool | ShowUser]:
    try:
        user = await users_service.activate_user(token)
    except InvalidTokenServiceError as e:
        raise HTTPException(400, e.args[0]) from e
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return {"activated": True, "user": user}
