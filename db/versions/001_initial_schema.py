"""initial_schema

Revision ID: 001
Revises:
Create Date: 2026-04-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fridge_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "item_name", name="uq_fridge_items_user_item"),
    )

    op.create_table(
        "condiments_catalog",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("default_unit", sa.String(50), nullable=True),
    )

    op.create_table(
        "recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source_url", sa.Text, unique=True, nullable=False),
        sa.Column("ingredients", postgresql.JSONB, nullable=False),
        sa.Column("steps", postgresql.JSONB, nullable=False),
        sa.Column("cuisine", sa.String(100), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("scraped_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "recipe_ingredients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
    )

    op.create_index("ix_recipe_ingredients_canonical_name", "recipe_ingredients", ["canonical_name"])
    op.execute("CREATE INDEX ON recipes USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")
    op.drop_table("condiments_catalog")
    op.drop_table("fridge_items")
    op.drop_table("users")
