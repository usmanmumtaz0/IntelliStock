"""Enforce uniqueness for normalized user email addresses.

Revision ID: 0002_normalized_user_email
Revises: 0001_existing_schema_baseline
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_normalized_user_email"
down_revision = "0001_existing_schema_baseline"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_users_email_normalized"


def _index_exists(bind) -> bool:
    if bind.dialect.name == "sqlite":
        return bind.execute(
            sa.text("SELECT 1 FROM sqlite_master WHERE type='index' AND name=:name"),
            {"name": INDEX_NAME},
        ).first() is not None
    return INDEX_NAME in {index["name"] for index in sa.inspect(bind).get_indexes("users")}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    duplicate = bind.execute(
        sa.text(
            "SELECT lower(email) AS normalized_email, count(*) AS total "
            "FROM users GROUP BY lower(email) HAVING count(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate:
        raise RuntimeError(
            "Cannot add normalized email uniqueness: resolve case-insensitive duplicate users first"
        )

    if not _index_exists(bind):
        op.execute(sa.text(f"CREATE UNIQUE INDEX {INDEX_NAME} ON users (lower(email))"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names():
        if _index_exists(bind):
            op.drop_index(INDEX_NAME, table_name="users")
