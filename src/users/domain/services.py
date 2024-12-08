from core.service import BaseService

from users.schemas import CreateUserDTO


class UsersService(BaseService):
    entity_name = "User"

    async def register(self, dto: CreateUserDTO): ...
