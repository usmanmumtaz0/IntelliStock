"""Operational requests and revocable account sessions; preserve existing users."""
from alembic import op
import sqlalchemy as sa

revision = "0008_rbac_requests_sessions"
down_revision = "0007_backend_table_privacy"
branch_labels = None
depends_on = None
PROTECTED_TABLES = ("operational_requests",)


def upgrade():
    bind = op.get_bind()
    if "session_version" not in {c["name"] for c in sa.inspect(bind).get_columns("users")}:
        op.add_column("users", sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"))
    from app.models.operational_request import OperationalRequest
    OperationalRequest.__table__.create(bind, checkfirst=True)
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE public.operational_requests ENABLE ROW LEVEL SECURITY')
        op.execute('REVOKE ALL ON TABLE public.operational_requests FROM PUBLIC')
        for role in ("anon", "authenticated"):
            if bind.execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}).scalar():
                op.execute(f'REVOKE ALL ON TABLE public.operational_requests FROM "{role}"')


def downgrade():
    # Preserve submissions and token revocation counters on code rollback.
    pass
