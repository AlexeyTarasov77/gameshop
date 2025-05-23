"""new Product.orig_url field

Revision ID: 69410d64bdf6
Revises: f3315acffeef
Create Date: 2025-05-05 12:47:16.217941

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "69410d64bdf6"
down_revision: Union[str, None] = "f3315acffeef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("product", sa.Column("orig_url", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("product", "orig_url")
    # ### end Alembic commands ###
