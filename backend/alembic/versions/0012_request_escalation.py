"""Add explicit manager-to-admin request escalation routing."""
from alembic import op
import sqlalchemy as sa

revision = "0012_request_escalation"
down_revision = "0011_product_identity"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("operational_requests")}
    if "review_tier" not in columns:
        op.add_column(
            "operational_requests",
            sa.Column("review_tier", sa.String(16), nullable=False, server_default="manager"),
        )
        op.create_index("ix_operational_requests_review_tier", "operational_requests", ["review_tier"])


def downgrade():
    # Preserve workflow routing data on code rollback.
    pass