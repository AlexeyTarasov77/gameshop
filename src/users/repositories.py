from gateways.db.repository import SqlAlchemyRepository

from users.models import User


class UsersRepository(SqlAlchemyRepository[User]):
    model = User

    async def update_by_id(self, user_id: int, **data) -> User:
        return await super().update(data, id=user_id)

    async def get_by_email(self, email: str) -> User:
        return await super().get_one(email=email)
