from gateways.db.repository import SqlAlchemyRepository

from users.models import User


class UsersRepository(SqlAlchemyRepository[User]):
    model = User
