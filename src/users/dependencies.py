from typing import Annotated
from users.domain.services import InvalidTokenServiceError, UsersService
from core.ioc import Inject
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer

UsersServiceDep = Annotated[UsersService, Inject(UsersService)]


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


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
    except InvalidTokenServiceError as e:
        raise credentials_exception from e


async def get_optional_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)], users_service: UsersServiceDep
) -> int | None:
    if token:
        return await get_user_id_or_raise(token, users_service)
    return None
