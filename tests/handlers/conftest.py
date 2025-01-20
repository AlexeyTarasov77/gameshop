import sys
import os
from pathlib import Path

from httpx import URL


os.environ["MODE"] = "tests"
sys.path.insert(1, str((Path().parent / "src").absolute()))


from core.ioc import Resolve
from core.router import router as core_router
from faker import Faker
from fastapi.testclient import TestClient
from gateways.db.main import SqlAlchemyDatabase
from main import app_factory

from config import Config

cfg = Resolve(Config)
db = Resolve(SqlAlchemyDatabase)
client = TestClient(app_factory())
client.base_url = URL(f"http://{cfg.server.host}:{cfg.server.port}{core_router.prefix}")
fake = Faker()
