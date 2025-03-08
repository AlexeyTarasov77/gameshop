from json import JSONDecoder, JSONEncoder
from typing import Any, NamedTuple
from sales import APP_LABEL as SALES_APP_LABEL
from redis.asyncio import Redis
from redis.commands.json import JSON


class RedisJSONEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        try:
            return str(o)
        except Exception:
            return super().default(o)


class IndexInfo(NamedTuple):
    for_prefix: str
    name: str


indexes = {SALES_APP_LABEL: IndexInfo("sales_item:", "idx:sales")}


def init_redis_client(dsn: str) -> Redis:
    r = Redis.from_url(dsn)
    old_json = r.json

    def _json_monkeypatch(encoder=RedisJSONEncoder(), decoder=JSONDecoder()) -> JSON:
        return old_json(encoder, decoder)

    r.json = _json_monkeypatch

    return r
