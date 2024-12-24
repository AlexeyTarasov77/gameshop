from datetime import datetime
from core.schemas import Base64Int, BaseModel


class ShowNews(BaseModel):
    id: Base64Int
    description: str
    photo_url: str | None
    created_at: datetime
    updated_at: datetime


class CreateNewsDTO(BaseModel):
    description: str
    photo_url: str | None


class UpdateNewsDTO(BaseModel):
    description: str | None
    photo_url: str | None
