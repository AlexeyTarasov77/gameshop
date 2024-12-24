from datetime import datetime

from core.schemas import Base64Int, BaseDTO, UrlStr


class ShowNews(BaseDTO):
    id: Base64Int
    title: str
    description: str
    photo_url: UrlStr | None
    created_at: datetime
    updated_at: datetime


class CreateNewsDTO(BaseDTO):
    title: str
    description: str
    photo_url: UrlStr | None = None


class UpdateNewsDTO(BaseDTO):
    title: str = None
    description: str = None
    photo_url: UrlStr | None = None
