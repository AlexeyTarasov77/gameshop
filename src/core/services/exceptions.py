class ServiceError(Exception):
    def _generate_msg(self) -> str:
        return "unexpected service error"

    def __init__(self, entity_name: str = "Unknown", *args, **kwargs) -> None:
        self._entity_name = entity_name
        self._params = kwargs
        self.msg = self._generate_msg()
        return super().__init__(*args)


class EntityNotFoundError(ServiceError):
    def _generate_msg(self) -> str:
        msg = "%s %s not found"
        params_string = ""
        if self._params:
            params_string = "with " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)


class EntityAlreadyExistsError(ServiceError):
    def _generate_msg(self) -> str:
        msg = "%s %s already exists"
        params_string = ""
        if self._params:
            params_string += "with " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)


class EntityRelatedResourceNotFoundError(ServiceError):
    def _generate_msg(self) -> str:
        msg = "%s's related resources doesn't exist%s"
        params_string = ""
        if self._params:
            params_string += ": " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)
