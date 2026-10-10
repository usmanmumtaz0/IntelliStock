"""Persist email delivery attempts without changing existing alerts."""
from alembic import op
from app.models.notification import NotificationDelivery

revision = "0004_notification_delivery"
down_revision = "0003_delivery_pipeline"
branch_labels = depends_on = None


def upgrade():
    NotificationDelivery.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    # Delivery history must not be destroyed by an application rollback.
    pass
