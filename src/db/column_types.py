from datetime import datetime
from typing import Annotated

from sqlalchemy import text
from sqlalchemy.orm import mapped_column

int_pk_type = Annotated[int, mapped_column(primary_key=True)]

created_at_t = Annotated[datetime, mapped_column(server_default=text("now()"))]
updated_at_t = Annotated[
    datetime, mapped_column(server_default=text("now()"), server_onupdate=text("now()"))
]
