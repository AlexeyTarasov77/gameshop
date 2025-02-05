class ServiceError(Exception):
    def __init__(self, msg: str) -> None:
        self.msg = msg
        return super().__init__()


class MappedServiceError(ServiceError):
    msg: str

    def _generate_msg(self) -> str:
        return "unexpected service error"

    def __init__(self, entity_name: str, **kwargs) -> None:
        self._entity_name = entity_name
        self._params = kwargs
        return super().__init__(self._generate_msg())


class EntityNotFoundError(MappedServiceError):
    def _generate_msg(self) -> str:
        msg = "%s %s not found"
        params_string = ""
        if self._params:
            params_string = "with " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)


class EntityAlreadyExistsError(MappedServiceError):
    def _generate_msg(self) -> str:
        msg = "%s %s already exists"
        params_string = ""
        if self._params:
            params_string += "with " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)


class EntityRelatedResourceNotFoundError(MappedServiceError):
    def _generate_msg(self) -> str:
        msg = "%s's related resources doesn't exist%s"
        params_string = ""
        if self._params:
            params_string += ": " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)
