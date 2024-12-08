import typing as t

from users.schemas import CreateUserDTO


class UsersRepositoryI(t.Protocol):
    async def create(self, dto: CreateUserDTO): ...
