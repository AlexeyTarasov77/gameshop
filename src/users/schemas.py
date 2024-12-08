from datetime import datetime

from core.schemas import BaseDTO, Image
from pydantic import EmailStr, field_validator


class CreateUserDTO(BaseDTO):
    email: EmailStr
    password: str
    photo: Image | None = None

    @field_validator("password")
    @classmethod
    def validate_password[T: str](cls, value: T) -> T:
        if len(str(value)) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value


class ShowUser(BaseDTO):
    id: int
    email: EmailStr
    photo_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
