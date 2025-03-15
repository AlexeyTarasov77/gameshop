import typing as t

from fastapi.responses import JSONResponse
from pydantic import EmailStr

from core.dependencies import SessionKeyDep, restrict_content_type
from core.schemas import require_dto_not_empty
from users.dependencies import (
    UsersServiceDep,
    get_user_id_or_raise,
)
from fastapi import (
    APIRouter,
    Body,
    Depends,
    Form,
    status,
)

from users import schemas

router = APIRouter(prefix="/users", tags=["users", "auth"])


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    dependencies=[restrict_content_type("multipart/form-data")],
)
async def signup(
    dto: t.Annotated[schemas.CreateUserDTO, Form(media_type="multipart/form-data")],
    users_service: UsersServiceDep,
) -> schemas.ShowUser | JSONResponse:
    return await users_service.signup(dto)


@router.post("/signin")
async def signin(
    dto: schemas.UserSignInDTO,
    users_service: UsersServiceDep,
    session_key: SessionKeyDep,
) -> dict[str, str]:
    token = await users_service.signin(dto, session_key)
    return {"token": token}


@router.patch(
    "/update",
    dependencies=[restrict_content_type("multipart/form-data")],
)
async def update_user(
    dto: t.Annotated[schemas.UpdateUserDTO, Form(media_type="multipart/form-data")],
    user_id: t.Annotated[int, Depends(get_user_id_or_raise)],
    users_service: UsersServiceDep,
):
    require_dto_not_empty(dto)
    user, verification_email_sent = await users_service.update_user(dto, user_id)
    return {"data": user, "verification_email_sent": verification_email_sent}


@router.patch("/email-confirm")
async def update_email_confirm(
    user_id: t.Annotated[int, Depends(get_user_id_or_raise)],
    users_service: UsersServiceDep,
    token: t.Annotated[str, Body(min_length=15, embed=True)],
) -> schemas.ShowUser:
    return await users_service.update_email_confirm(user_id, token)


@router.patch("/activate")
async def activate_user(
    token: t.Annotated[str, Body(min_length=15, embed=True)],
    users_service: UsersServiceDep,
) -> schemas.ShowUser:
    return await users_service.activate_user(token)


@router.post("/resend-activation-token", status_code=status.HTTP_202_ACCEPTED)
async def resend_activation_token(
    email: t.Annotated[EmailStr, Body(embed=True)], users_service: UsersServiceDep
) -> None:
    await users_service.resend_activation_token(email)


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
async def send_password_reset_token(
    email: t.Annotated[EmailStr, Body(embed=True)], users_service: UsersServiceDep
) -> None:
    await users_service.send_password_reset_token(email)


@router.patch("/password-update")
async def update_password(
    dto: schemas.UpdatePasswordDTO,
    users_service: UsersServiceDep,
):
    await users_service.update_password(dto.new_password, dto.token)
    return {"success": True}


@router.get("/get-by-token")
async def get_user_by_token(
    user_id: t.Annotated[int, Depends(get_user_id_or_raise)],
    users_service: UsersServiceDep,
) -> schemas.ShowUserWithRole:
    return await users_service.get_user_with_role(user_id)
