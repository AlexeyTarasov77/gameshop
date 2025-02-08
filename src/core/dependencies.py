from typing import Annotated
from fastapi import HTTPException, Header, status, Depends
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
