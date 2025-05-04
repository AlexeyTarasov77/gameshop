from typing import Annotated
from users.domain.services import UsersService
from core.ioc import Inject
from config import Config, ConfigMode
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer

UsersServiceDep = Annotated[UsersService, Inject(UsersService)]


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/signin", auto_error=False)
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Unauthorized",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_user_id_or_raise(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    users_service: UsersServiceDep,
):
    if not token:
        raise credentials_exception from None
    return await users_service.extract_and_validate_user_id_from_token(token)


async def get_optional_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    users_service: UsersServiceDep,
) -> int | None:
    if token:
        return await get_user_id_or_raise(token, users_service)
    return None


async def require_admin(
    user_id: Annotated[int | None, Depends(get_optional_user_id)],
    users_service: UsersServiceDep,
    cfg: Annotated[Config, Inject(Config)],
) -> None:
    # flag to change, if wanna test require_admin functionallity in local mode
    require_admin_in_debug = False
    if cfg.mode == ConfigMode.LOCAL and not require_admin_in_debug:
        return
    if not user_id:
        raise credentials_exception from None
    is_admin = await users_service.check_is_user_admin(user_id)
    if not is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
