"""Distinguish pending public signups from disabled existing accounts."""
from alembic import op
import sqlalchemy as sa

revision = "0006_signup_approval"
down_revision = "0005_private_chat"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        from app.models.user import User
        User.__table__.create(bind=bind, checkfirst=True)
    elif "signup_pending" not in {column["name"] for column in inspector.get_columns("users")}:
        op.add_column("users", sa.Column("signup_pending", sa.Boolean(), nullable=False,
                                         server_default=sa.false()))
    if bind.dialect.name == "postgresql":
        # Backend uses its database owner connection, not Supabase browser roles.
        # No browser-side policies: password hashes must never be Data API data.
        op.execute(sa.text('ALTER TABLE users ENABLE ROW LEVEL SECURITY'))
        for role in ("anon", "authenticated"):
            if bind.execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}).scalar():
                op.execute(sa.text(f'REVOKE ALL ON TABLE users FROM "{role}"'))


def downgrade():
    # Preserve approval state; reverting code is not permission to activate users.
    pass
