"""Create missing tables for the reviewed pre-Alembic IntelliStock schema.

Revision ID: 0001_existing_schema_baseline
Revises: None

The project originally used ``metadata.create_all``. This idempotent baseline lets
an existing installation be stamped/upgraded without dropping populated tables,
while creating the same schema on a new database.
"""
from alembic import op
from sqlalchemy import inspect

from app.models import Base

revision = "0001_existing_schema_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing:
            table.create(bind=bind)


def downgrade() -> None:
    # Dropping the entire pre-existing application schema is unsafe. Individual
    # incremental revisions provide reversible downgrades where appropriate.
    pass
