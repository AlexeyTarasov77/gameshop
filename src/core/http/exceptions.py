from core.service import ServiceError


class HttpExceptionsMapper:
    """Maps service errors to corresponding http exception"""

    @classmethod
    def map(cls, exc: ServiceError): ...
