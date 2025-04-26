from core.utils.helpers import normalize_s


class ServiceError(Exception):
    _msg = "unexpected service error"

    def __init__(self, msg: str | None = None) -> None:
        self._msg = msg or self._msg
        return super().__init__()

    def __str__(self):
        return self._msg


class UnavailableProductError(ServiceError):
    def __init__(self, product_name: str, region: str | None = None):
        msg = f"Can't create order! Product {product_name} is not available"
        if region is not None:
            msg += " in region: " + normalize_s(region)
        super().__init__(msg)


class ClientError(ServiceError):
    _msg = "client error"


class TokenError(ServiceError): ...


class ExpiredTokenError(TokenError):
    _msg = "Token expired! Please refresh your token."


class InvalidTokenError(TokenError):
    _msg = "Invalid token. Please obtain a new token and try again."


class UserIsNotActivatedError(ServiceError):
    _msg = "User isn't activated. Check your email to activate account and try to signin again!"


class InvalidCredentialsError(ServiceError):
    _msg = "Invalid email or password"


class UserAlreadyActivatedError(ServiceError):
    _msg = "User already activated!"


class ActionForbiddenError(ServiceError):
    _msg = "Action forbidden"


class ExternalGatewayError(ServiceError):
    _msg = "Gateway error. Please try again later"


class CommonServiceError(ServiceError):
    def _generate_msg(self) -> str:
        return self._msg

    def __init__(self, entity_name: str, **kwargs) -> None:
        self._entity_name = entity_name
        self._params = kwargs
        return super().__init__(self._generate_msg())


class EntityNotFoundError(CommonServiceError):
    def _generate_msg(self) -> str:
        msg = "%s %s not found"
        params_string = ""
        if self._params:
            params_string = "with " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)


class EntityAlreadyExistsError(CommonServiceError):
    def _generate_msg(self) -> str:
        msg = "%s %s already exists"
        params_string = ""
        if self._params:
            params_string += "with " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)


class EntityOperationRestrictedByRefError(CommonServiceError):
    def _generate_msg(self) -> str:
        msg = "Can't delete %s, because it is referenced from another model"
        return msg % self._entity_name


class EntityRelationshipNotFoundError(CommonServiceError):
    def _generate_msg(self) -> str:
        msg = "%s's relationship doesn't exist%s"
        params_string = ""
        if self._params:
            params_string += ": " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)
