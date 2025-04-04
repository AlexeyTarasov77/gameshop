from datetime import datetime
from typing import Annotated

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import mapped_column

int_pk_type = Annotated[int, mapped_column(primary_key=True)]
_pg_utcnow = text("now() at time zone 'UTC'")
created_at_type = Annotated[datetime, mapped_column(server_default=_pg_utcnow)]
updated_at_type = Annotated[
    datetime, mapped_column(server_default=_pg_utcnow, server_onupdate=_pg_utcnow)
]
timestamptz = Annotated[datetime, mapped_column(TIMESTAMP(timezone=True))]
