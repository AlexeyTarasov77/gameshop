from datetime import datetime
from core.schemas import Base64Int, BaseModel


class ShowNews(BaseModel):
    id: Base64Int
    description: str
    photo_url: str
    created_at: datetime
    updated_at: datetime
