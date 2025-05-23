"""created order related models

Revision ID: 255990c637c4
Revises: d3f0d91e7889
Create Date: 2025-01-06 13:32:23.192305

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "255990c637c4"
down_revision: Union[str, None] = "d3f0d91e7889"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "customer_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "order",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "order_date", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("customer_data_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("COMPLETED", "PENDING", "CANCELLED", name="orderstatus"),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.ForeignKeyConstraint(
            ["customer_data_id"], ["customer_data.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "order_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("price", sa.Numeric(), nullable=False),
        sa.Column(
            "quantity", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.ForeignKeyConstraint(["order_id"], ["order.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("order_item")
    op.drop_table("order")
    op.drop_table("customer_data")
    # ### end Alembic commands ###
