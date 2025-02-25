from datetime import datetime
from typing import Annotated

from core.schemas import Base64Int, BaseDTO, ImgUrl, UploadImage
from pydantic import AfterValidator, EmailStr, model_validator


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


class UpdateUserDTO(BaseDTO):
    username: str | None = None
    email: EmailStr | None = None
    photo: UploadImage | None = None


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

    @model_validator(mode="after")
    def set_default_photo_url(self):
        if self.photo_url is None:
            self.photo_url = f"https://robohash.org/{self.id}"
        return self


class ShowUserWithRole(ShowUser):
    is_admin: bool
