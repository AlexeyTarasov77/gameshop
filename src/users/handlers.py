import typing as t
from http import HTTPStatus

from fastapi.responses import JSONResponse
from pydantic import EmailStr

from core.exception_mappers import HttpExceptionsMapper
from core.services.exceptions import EntityNotFoundError, ServiceError
from users.dependencies import UsersServiceDep, get_user_id_or_raise
from fastapi import (
    APIRouter,
    Body,
    Depends,
    Form,
    HTTPException,
    Request,
    status,
)

from users import schemas
from users.domain.services import (
    InvalidTokenServiceError,
    PasswordDoesNotMatchError,
    UserAlreadyActivatedError,
    UserIsNotActivatedError,
)

router = APIRouter(prefix="/users", tags=["users", "auth"])


@router.post("/signup", status_code=HTTPStatus.CREATED, response_model=None)
async def signup(
    req: Request,
    dto: t.Annotated[schemas.CreateUserDTO, Form()],
    users_service: UsersServiceDep,
) -> schemas.ShowUser | JSONResponse:
    try:
        return await users_service.signup(dto)
    except UserIsNotActivatedError:
        return JSONResponse(
            {"redirect_url": str(req.url_for("resend_activation_token"))},
            status.HTTP_403_FORBIDDEN,
        )
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
    except UserIsNotActivatedError as e:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "User isn't activated. Check your email to activate account and try to signin again!",
        ) from e
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return {"token": token}


@router.patch("/activate")
async def activate_user(
    token: t.Annotated[str, Body(min_length=15, embed=True)],
    users_service: UsersServiceDep,
) -> dict[str, bool | schemas.ShowUser]:
    try:
        user = await users_service.activate_user(token)
    except InvalidTokenServiceError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, e.args[0]) from e
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return {"activated": True, "user": user}


@router.post("/resend-activation-token", status_code=status.HTTP_202_ACCEPTED)
async def resend_activation_token(
    email: t.Annotated[EmailStr, Body(embed=True)], users_service: UsersServiceDep
) -> None:
    try:
        await users_service.resend_activation_token(email)
    except UserAlreadyActivatedError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "User already activated"
        ) from e
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)


@router.get("/get-by-token")
async def get_user_by_token(
    user_id: t.Annotated[int, Depends(get_user_id_or_raise)],
    users_service: UsersServiceDep,
) -> schemas.ShowUserWithRole:
    try:
        return await users_service.get_user(user_id)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
