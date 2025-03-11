from sqlalchemy import select, update
from core.utils import UnspecifiedType
from gateways.db.exceptions import NotFoundError
from gateways.db.sqlalchemy_gateway import SqlAlchemyRepository
from users.schemas import CreateUserDTO
from users.models import Admin, Token, TokenScopes, User


class UsersRepository(SqlAlchemyRepository[User]):
    model = User

    async def mark_as_active(self, user_id: int) -> User:
        return await super().update({"is_active": True}, id=user_id)

    async def get_by_email(self, email: str) -> User:
        return await super().get_one(email=email)

    async def create_with_hashed_password(
        self, dto: CreateUserDTO, password_hash: bytes, photo_url: str | None
    ) -> User:
        data = dto.model_dump(exclude={"password", "photo"})
        return await super().create(
            password_hash=password_hash, photo_url=photo_url, **data
        )

    async def check_exists_active(self, user_id: int) -> bool:
        stmt = select(1).select_from(self.model).filter_by(is_active=True, id=user_id)
        res = await self._session.execute(stmt)
        return bool(res.one_or_none())

    async def update_by_id(
        self,
        user_id: int,
        username: str | None = None,
        photo_url: str | None | UnspecifiedType = ...,
        email: str | None = None,
    ) -> User:
        data = {}
        if username is not None:
            data["username"] = username
        if photo_url is not ...:
            data["photo_url"] = photo_url
        if email is not None:
            data["email"] = email
        return await super().update(data, id=user_id)

    async def get_by_id(self, user_id: int, is_active: bool | None = None) -> User:
        filter_by = {"id": user_id}
        if is_active is not None:
            filter_by["is_active"] = is_active
        return await super().get_one(**filter_by)

    async def set_new_password(self, user_id: int, password_hash: bytes) -> None:
        stmt = (
            update(User)
            .values(password_hash=password_hash)
            .filter_by(id=user_id)
            .returning(User.id)
        )
        res = await self._session.execute(stmt)
        if res.scalar_one_or_none() is None:
            raise NotFoundError()

    async def get_by_id_and_check_is_admin(
        self,
        user_id: int,
    ) -> tuple[User, bool]:
        stmt = (
            select(User, Admin.user_id)
            .join(Admin, Admin.user_id == User.id, isouter=True)
            .where(User.id == user_id)
        )
        res = await self._session.execute(stmt)
        data = res.one_or_none()
        if data is None:
            raise NotFoundError(f"User with id: {user_id} not found")
        return data[0], bool(data[1])


class TokensRepository(SqlAlchemyRepository[Token]):
    model = Token

    async def save(self, token: Token) -> None:
        self._session.add(token)
        await self._session.flush()

    async def get_by_hash(self, hash: bytes, scope: TokenScopes) -> Token:
        return await super().get_one(hash=hash, scope=scope)

    async def delete_all_for_user(self, user_id: int, scope: TokenScopes) -> None:
        await super().delete(user_id=user_id, scope=scope)


class AdminsRepository(SqlAlchemyRepository[Admin]):
    model = Admin

    async def check_exists(self, user_id: int) -> bool:
        stmt = select(1).select_from(self.model).filter_by(user_id=user_id)
        res = await self._session.execute(stmt)
        return bool(res.scalar_one_or_none())
