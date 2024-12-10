import sys
from pathlib import Path

from httpx import URL

sys.path.insert(1, str((Path().parent / "src").absolute()))

import typing as t

from core.ioc import get_container
from core.router import router as core_router
from faker import Faker
from fastapi.testclient import TestClient
from gateways.db.main import SqlAlchemyDatabase
from main import app_factory

from config import Config

container = get_container()
cfg = t.cast(Config, container.resolve(Config))
db = t.cast(SqlAlchemyDatabase, container.resolve(SqlAlchemyDatabase))
client = TestClient(app_factory())
client.base_url = URL(f"http://{cfg.server.host}:{cfg.server.port}{core_router.prefix}")
faker = Faker()
faker = Faker()
