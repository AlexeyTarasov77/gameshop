class ServiceError(Exception):
    def __init__(self, msg: str) -> None:
        self._msg = msg
        return super().__init__()

    def __str__(self):
        return self._msg


class CommonServiceError(ServiceError):
    def _generate_msg(self) -> str:
        return "unexpected service error"

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
