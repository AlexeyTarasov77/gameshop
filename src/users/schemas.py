from datetime import datetime

from core.schemas import Base64Int, BaseDTO, ImgUrl, UploadImage
from pydantic import EmailStr, field_validator


class CreateUserDTO(BaseDTO):
    username: str
    email: EmailStr
    password: str
    photo: UploadImage | None = None

    @field_validator("password")
    @classmethod
    def validate_password[T: str](cls, value: T) -> T:
        if len(str(value)) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value


class UserSignInDTO(BaseDTO):
    email: EmailStr
    password: str


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
