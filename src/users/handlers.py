import typing as t
from http import HTTPStatus

from core.ioc import Inject
from fastapi import APIRouter, Form

from users.domain.services import UsersService
from users.schemas import CreateUserDTO

router = APIRouter(prefix="/users", tags=["users", "auth"])


@router.post("/signup", status_code=HTTPStatus.CREATED)
async def signup(
    dto: t.Annotated[CreateUserDTO, Form()],
    users_service: t.Annotated[UsersService, Inject(UsersService)],
): ...
