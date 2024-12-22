from gateways.db.repository import SqlAlchemyRepository
from news.models import News


class NewsRepository(SqlAlchemyRepository[News]):
    model = News
