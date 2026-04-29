"""Add extended-feature columns to items (short_description, top_rated_seller,
shipping_cost, free_shipping, watch_count, image_count).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("items", sa.Column("short_description", sa.Text(), nullable=True))
    op.add_column("items", sa.Column("top_rated_seller", sa.Boolean(), nullable=True))
    op.add_column("items", sa.Column("shipping_cost", sa.Numeric(10, 2), nullable=True))
    op.add_column("items", sa.Column("free_shipping", sa.Boolean(), nullable=True))
    op.add_column("items", sa.Column("watch_count", sa.Integer(), nullable=True))
    op.add_column("items", sa.Column("image_count", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("items", "image_count")
    op.drop_column("items", "watch_count")
    op.drop_column("items", "free_shipping")
    op.drop_column("items", "shipping_cost")
    op.drop_column("items", "top_rated_seller")
    op.drop_column("items", "short_description")
