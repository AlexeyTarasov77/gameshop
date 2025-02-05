from typing import Annotated
from users.domain.services import TokenError, UsersService
from core.ioc import Inject
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer

UsersServiceDep = Annotated[UsersService, Inject(UsersService)]


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="signin", auto_error=False)


async def get_user_id_or_raise(
    token: Annotated[str | None, Depends(oauth2_scheme)], users_service: UsersServiceDep
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception from None
    try:
        return await users_service.extract_user_id_from_token(token)
    except TokenError as e:
        raise credentials_exception from e


async def get_optional_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)], users_service: UsersServiceDep
) -> int | None:
    if token:
        return await get_user_id_or_raise(token, users_service)
    return None


async def require_admin(
    user_id: Annotated[int, Depends(get_user_id_or_raise)],
    users_service: UsersServiceDep,
) -> None:
    is_admin = await users_service.check_is_user_admin(user_id)
    if not is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
