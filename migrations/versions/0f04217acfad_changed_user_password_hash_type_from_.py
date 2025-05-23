"""Changed user.password_hash type from str to bytes

Revision ID: 0f04217acfad
Revises: 5e47d4faf307
Create Date: 2024-12-08 11:50:27.826651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0f04217acfad'
down_revision: Union[str, None] = '5e47d4faf307'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'password_hash',
               existing_type=sa.VARCHAR(),
               type_=postgresql.BYTEA(),
               existing_nullable=False, postgresql_using='password_hash::bytea')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'password_hash',
               existing_type=postgresql.BYTEA(),
               type_=sa.VARCHAR(),
               existing_nullable=False, postgresql_using='password_hash::text')
    # ### end Alembic commands ###
