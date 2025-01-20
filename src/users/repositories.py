from datetime import datetime, timedelta
from gateways.db.repository import SqlAlchemyRepository
from users.schemas import CreateUserDTO
from users.models import Token, User


class UsersRepository(SqlAlchemyRepository[User]):
    model = User

    async def update_by_id(self, user_id: int, **data) -> User:
        return await super().update(data, id=user_id)

    async def get_by_email(self, email: str) -> User:
        return await super().get_one(email=email)

    async def create_with_hashed_password(
        self, dto: CreateUserDTO, password_hash: bytes
    ) -> User:
        return await super().create(
            password_hash=password_hash, **dto.model_dump(exclude={"password"})
        )


class TokensRepository(SqlAlchemyRepository[Token]):
    model = Token

    async def create(self, hash: bytes, user_id: int, expires_in: timedelta) -> None:
        expiry = datetime.now() + expires_in
        await super().create(hash=hash, user_id=user_id, expiry=expiry)

    async def get_by_hash(self, hash: bytes) -> Token:
        return await super().get_one(hash=hash)
