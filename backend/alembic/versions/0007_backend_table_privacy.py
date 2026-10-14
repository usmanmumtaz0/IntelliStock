"""Restrict explicitly owned backend tables, without touching unrelated schemas."""
from alembic import op
import sqlalchemy as sa

revision = "0007_backend_table_privacy"
down_revision = "0006_signup_approval"
branch_labels = None
depends_on = None

TABLES = (
    "agent_runs", "alembic_version", "alerts", "audit_logs", "cameras",
    "chat_conversations", "chat_turns", "inventory", "inventory_events",
    "inventory_history", "notification_deliveries", "outbox_events",
    "performance_logs", "products", "shelf_zones", "system_health_metrics",
    "users", "zone_product_mappings",
)


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    existing = set(sa.inspect(bind).get_table_names(schema="public"))
    roles = [role for role in ("anon", "authenticated") if bind.execute(
        sa.text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}).scalar()]
    for table in TABLES:
        if table not in existing:
            continue
        # Runtime uses the table owner connection (RLS owner bypass), never browser roles.
        # Fail rather than silently locking a non-owner backend out of its own data.
        allowed = bind.execute(sa.text("""
            SELECT c.relowner = (SELECT oid FROM pg_roles WHERE rolname=current_user)
                   OR (SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user)
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname=:table
        """), {"table": table}).scalar()
        if not allowed:
            raise RuntimeError("Privacy migration requires the backend table owner or BYPASSRLS role")
        op.execute(sa.text(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'REVOKE ALL PRIVILEGES ON TABLE public."{table}" FROM PUBLIC'))
        for role in roles:
            op.execute(sa.text(f'REVOKE ALL PRIVILEGES ON TABLE public."{table}" FROM "{role}"'))


def downgrade():
    # A rollback must not silently republish private data.
    pass
