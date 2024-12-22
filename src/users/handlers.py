import typing as t
from http import HTTPStatus

from core.http.exceptions import HttpExceptionsMapper
from core.ioc import Inject
from core.service import EntityNotFoundError, ServiceError
from fastapi import APIRouter, Body, HTTPException

from users import schemas
from users.domain.services import (
    InvalidTokenServiceError,
    PasswordDoesNotMatchError,
    UsersService,
)

router = APIRouter(prefix="/users", tags=["users", "auth"])

UsersServiceDep = t.Annotated[UsersService, Inject(UsersService)]


@router.post("/signup", status_code=HTTPStatus.CREATED)
async def signup(
    dto: schemas.CreateUserDTO,
    users_service: UsersServiceDep,
) -> schemas.ShowUser:
    try:
        return await users_service.signup(dto)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)


@router.post("/signin")
async def signin(
    dto: schemas.UserSignInDTO, users_service: UsersServiceDep
) -> dict[str, str]:
    try:
        token = await users_service.signin(dto)
    except (EntityNotFoundError, PasswordDoesNotMatchError) as e:
        raise HTTPException(HTTPStatus.UNAUTHORIZED, "Invalid email or password") from e
    return {"token": token}


@router.patch("/activate")
async def activate_user(
    token: t.Annotated[str, Body(min_length=100, embed=True)],
    users_service: UsersServiceDep,
) -> dict[str, bool | schemas.ShowUser]:
    try:
        user = await users_service.activate_user(token)
    except InvalidTokenServiceError as e:
        raise HTTPException(400, e.args[0]) from e
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return {"activated": True, "user": user}
