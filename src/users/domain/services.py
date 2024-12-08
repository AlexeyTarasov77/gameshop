from core.service import BaseService

from users.schemas import CreateUserDTO


class UsersService(BaseService):
    entity_name = "User"

    async def signup(self, dto: CreateUserDTO): ...
