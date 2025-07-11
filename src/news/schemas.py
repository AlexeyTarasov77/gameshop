from datetime import datetime

from core.api.schemas import Base64Int, BaseDTO, ImgUrl, UploadImage


class ShowNews(BaseDTO):
    id: Base64Int
    title: str
    description: str
    photo_url: ImgUrl | None
    created_at: datetime
    updated_at: datetime


class CreateNewsDTO(BaseDTO):
    title: str
    description: str
    photo: UploadImage | None = None


class UpdateNewsDTO(BaseDTO):
    title: str | None = None
    description: str | None = None
    photo: UploadImage | None = None
