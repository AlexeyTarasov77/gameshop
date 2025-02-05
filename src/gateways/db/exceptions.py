class DatabaseError(Exception):
    def __init__(self, msg: str | None = None):
        self.msg = msg


class DBConnectionError(DatabaseError): ...


class NotFoundError(DatabaseError): ...


class AlreadyExistsError(DatabaseError): ...


class RelatedResourceNotFoundError(DatabaseError): ...
