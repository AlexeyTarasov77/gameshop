from typing import Annotated
from fastapi import HTTPException, Header, Request, status, Depends
from config import Config
from core.ioc import Resolve
from core.api.pagination import PaginationParams


def restrict_content_type(required_ct: str):
    def check_content_type(content_type: Annotated[str | None, Header()] = None):
        if content_type and not content_type.startswith(required_ct):
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                f"Unsupported Content-Type: {content_type}. It must be: {required_ct}",
            )

    return Depends(check_content_type)


PaginationDep = Annotated[PaginationParams, Depends()]


def get_session_key(req: Request):
    key_name = Resolve(Config).server.sessions.key
    session_id = req.scope.get(key_name)
    assert session_id, f"Missing {key_name} in req scope: {req.scope}"
    return session_id


SessionKeyDep = Annotated[str, Depends(get_session_key)]
