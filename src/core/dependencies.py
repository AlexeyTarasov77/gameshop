from typing import Annotated
from fastapi import HTTPException, Header, Request, status, Depends
from config import Config
from core.ioc import Resolve
from core.pagination import PaginationParams


def restrict_content_type(required_ct: str):
    def check_content_type(content_type: Annotated[str | None, Header()] = None):
        if content_type and not content_type.startswith(required_ct):
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                f"Unsupported Content-Type: {content_type}. It must be: {required_ct}",
            )

    return Depends(check_content_type)


PaginationDep = Annotated[PaginationParams, Depends()]


def get_session_id(req: Request):
    session_id = req.scope.get(Resolve(Config).server.sessions.key)
    assert session_id, "Missing session_id in req scope: %s" % req.scope
    return session_id


SessionIdDep = Annotated[str, Depends(get_session_id)]
