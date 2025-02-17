from datetime import datetime
from typing import Annotated

from core.schemas import Base64Int, BaseDTO, ImgUrl, UploadImage
from pydantic import AfterValidator, EmailStr


def validate_password(password: str) -> str:
    assert len(password) >= 8, "Password must be at least 8 characters long"
    return password


PasswordField = Annotated[str, AfterValidator(validate_password)]


class CreateUserDTO(BaseDTO):
    username: str
    email: EmailStr
    password: PasswordField
    photo: UploadImage | None = None


class UserSignInDTO(BaseDTO):
    email: EmailStr
    password: str


class UpdatePasswordDTO(BaseDTO):
    new_password: PasswordField
    token: str


class ShowUser(BaseDTO):
    id: Base64Int
    username: str
    email: EmailStr
    photo_url: ImgUrl | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ShowUserWithRole(ShowUser):
    is_admin: bool
