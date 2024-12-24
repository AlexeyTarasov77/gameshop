import base64
from typing import Any

from core.pagination import PaginatedResponse


def is_base64(s: str) -> bool:
    try:
        return base64.b64encode(base64.b64decode(s)).decode() == s
    except Exception:
        return False


def base64_to_int(s: str) -> int:
    return int(base64.b64decode(s).decode())


def check_paginated_response(
    objects_key: str, data: dict[str, Any], params: dict[str, int] | None
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
