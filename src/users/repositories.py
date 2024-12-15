from gateways.db.exceptions import NotFoundError
from gateways.db.repository import SqlAlchemyRepository

from users.models import User


class UsersRepository(SqlAlchemyRepository[User]):
    model = User

    async def create(self, email: str, password_hash: bytes, photo_url: str | None) -> User:
        return await super().create(email=email, password_hash=password_hash, photo_url=photo_url)

    async def update(self, user_id: int, **data) -> User:
        return await super().update(data, id=user_id)

    async def get_by_email(self, email: str) -> User:
        res = await self.list(email=email)
        if not res:
            raise NotFoundError()
        return res[0]
