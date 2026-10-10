"""Durable outbox, SKU mappings and alert lifecycle fields."""
from alembic import op
import sqlalchemy as sa
from app.models.delivery import OutboxEvent, ZoneProductMapping

revision = "0003_delivery_pipeline"
down_revision = "0002_normalized_user_email"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    for table in (OutboxEvent.__table__, ZoneProductMapping.__table__):
        table.create(bind, checkfirst=True)
    columns = {c["name"] for c in sa.inspect(bind).get_columns("alerts")}
    if "snoozed_until" not in columns:
        op.add_column("alerts", sa.Column("snoozed_until", sa.DateTime(), nullable=True))
    if "active_key" not in columns:
        op.add_column("alerts", sa.Column("active_key", sa.String(160), nullable=True))
        op.create_index("uq_alert_active_key", "alerts", ["active_key"], unique=True)
    if "uq_inventory_zone_product" not in {i["name"] for i in sa.inspect(bind).get_indexes("inventory")}:
        duplicate = bind.execute(sa.text("SELECT zone_id, product_id FROM inventory "
            "GROUP BY zone_id, product_id HAVING count(*) > 1 LIMIT 1")).first()
        if duplicate:
            raise RuntimeError("Resolve duplicate inventory zone/product rows before upgrading; no data was deleted")
        op.create_index("uq_inventory_zone_product", "inventory", ["zone_id", "product_id"], unique=True)


def downgrade():
    # Preserve pending work and configuration on downgrade.
    pass
