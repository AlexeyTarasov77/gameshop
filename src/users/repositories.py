from gateways.db.repository import SqlAlchemyRepository

from users.models import User


class UsersRepository(SqlAlchemyRepository[User]):
    model = User

    async def create(self, email: str, password_hash: bytes, photo_url: str | None) -> User:
        return await super().create(email=email, password_hash=password_hash, photo_url=photo_url)
