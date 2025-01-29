from sqlalchemy import select
from core.utils import save_upload_file
from gateways.db.repository import SqlAlchemyRepository
from users.schemas import CreateUserDTO
from users.models import Admin, Token, User


class UsersRepository(SqlAlchemyRepository[User]):
    model = User

    async def mark_as_active(self, user_id: int) -> User:
        return await super().update({"is_active": True}, id=user_id)

    async def get_by_email(self, email: str) -> User:
        return await super().get_one(email=email)

    async def create_with_hashed_password(
        self, dto: CreateUserDTO, password_hash: bytes
    ) -> User:
        data = dto.model_dump(exclude={"password", "photo"})
        if dto.photo:
            data["photo_url"] = await save_upload_file(dto.photo)
        return await super().create(password_hash=password_hash, **data)

    async def get_by_id(self, user_id: int) -> User:
        return await super().get_one(id=user_id)


class TokensRepository(SqlAlchemyRepository[Token]):
    model = Token

    async def save(self, token: Token) -> None:
        self.session.add(token)
        await self.session.flush()

    async def get_by_hash(self, hash: bytes) -> Token:
        return await super().get_one(hash=hash)

    async def delete_all_for_user(self, user_id: int) -> None:
        await super().delete(user_id=user_id)


class AdminsRepository(SqlAlchemyRepository[Admin]):
    model = Admin

    async def check_exists(self, user_id: int) -> bool:
        stmt = select(1).select_from(self.model).filter_by(user_id=user_id)
        res = await self.session.execute(stmt)
        return bool(res.scalar_one_or_none())
