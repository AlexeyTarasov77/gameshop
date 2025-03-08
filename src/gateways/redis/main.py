from json import JSONDecoder, JSONEncoder
from typing import Any
import redis.asyncio as redis
from redis.commands.json import JSON


class RedisJSONEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        try:
            return str(o)
        except Exception:
            return super().default(o)


def init_redis_client(dsn: str) -> redis.Redis:
    r = redis.from_url(dsn)
    old_json = r.json

    def _json_monkeypatch(encoder=RedisJSONEncoder(), decoder=JSONDecoder()) -> JSON:
        return old_json(encoder, decoder)

    r.json = _json_monkeypatch

    return r
