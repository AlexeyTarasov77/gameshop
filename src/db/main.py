from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class Database:
    def __init__(self, storage_dsn: str, **engine_params) -> None:
        self.engine = create_async_engine(storage_dsn, **engine_params)
        self.session_factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
