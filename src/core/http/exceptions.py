from collections.abc import Mapping
from functools import partial
from http import HTTPStatus

from fastapi import HTTPException

from core.service import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    EntityRelatedResourceNotFoundError,
    ServiceError,
)
from core.utils import AbstractExceptionMapper


class HttpExceptionsMapper(AbstractExceptionMapper[ServiceError, HTTPException]):
    """Maps service errors to corresponding http status code"""

    EXCEPTION_MAPPING: Mapping[type[ServiceError], partial[HTTPException]] = {
        EntityNotFoundError: partial(HTTPException, status_code=HTTPStatus.NOT_FOUND),
        EntityAlreadyExistsError: partial(
            HTTPException, status_code=HTTPStatus.CONFLICT
        ),
        EntityRelatedResourceNotFoundError: partial(
            HTTPException, status_code=HTTPStatus.BAD_REQUEST
        ),
    }

    @classmethod
    def get_default_exc(cls):
        return partial(HTTPException, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    @classmethod
    def map(cls, exc):
        mapped_exc_class = super().map(exc)
        return partial(mapped_exc_class, detail=exc.msg)
