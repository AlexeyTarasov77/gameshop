import base64
from collections.abc import Generator
from logging import Logger
from typing import Any
from sqlalchemy.inspection import inspect
from core.ioc import Resolve
from handlers.conftest import db
from gateways.db.sqlalchemy_gateway import SqlAlchemyBaseModel
from core.api.pagination import PaginatedResponse
from sqlalchemy import delete, insert, select


def is_base64(s: str) -> bool:
    try:
        return base64.b64encode(base64.b64decode(s)).decode() == s
    except Exception:
        return False


def int_to_base64(n: int) -> str:
    return base64.b64encode(str(n).encode()).decode()


def base64_to_int(s: str) -> int:
    return int(base64.b64decode(s).decode())


pagination_test_cases = [
    (200, None),
    (200, {"page_size": 5, "page_num": 1}),
    (422, {"page_size": 0}),
    (422, {"page_num": 0}),
]


def check_paginated_response(
    objects_key: str, data: dict[str, Any], params: dict[str, Any] | None
):
    data_obj = PaginatedResponse.model_validate(data)
    assert objects_key in data
    assert data_obj.first_page == 1
    assert "last_page" in data and data["last_page"] == data_obj.last_page
    objects = data[objects_key]
    assert len(objects) == data_obj.total_on_page
    if params:
        if params.get("page_size"):
            assert data_obj.page_size == params["page_size"]
        if params.get("page_num"):
            assert data_obj.page_num == params["page_num"]


def create_model_obj[T: type[SqlAlchemyBaseModel]](
    model: T, **values
) -> Generator[T, Any, Any]:
    if not values:
        raise Exception("Empty values")
    pks = inspect(model).primary_key
    if len(pks) > 1:
        Resolve(Logger).warning("create_model_obj: %s has more than one pk", model)
    assert pks, f"{model} has no pk"
    pk_col_name = pks[0].name
    with db.sync_engine.begin() as conn:
        stmt = insert(model).values(**values).returning(model)
        res = conn.execute(stmt).first()
        assert res
        obj = model(**res._mapping)
    yield obj
    with db.sync_engine.begin() as conn:
        stmt = delete(model).filter_by(**{pk_col_name: getattr(obj, pk_col_name)})
        conn.execute(stmt)


def get_model_obj[T: type[SqlAlchemyBaseModel]](model: T, **filter_by) -> T | None:
    with db.sync_engine.begin() as conn:
        stmt = select(model).filter_by(**filter_by)
        res = conn.execute(stmt).first()
        if res is not None:
            return model(
                **{k: v for k, v in res._mapping.items() if k in model.__table__.c}
            )
        return None
