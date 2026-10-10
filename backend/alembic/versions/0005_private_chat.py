"""Owner-private conversations and idempotent chat turns."""
from alembic import op
from app.models.chat import ChatConversation, ChatTurn

revision = "0005_private_chat"
down_revision = "0004_notification_delivery"
branch_labels = depends_on = None


def upgrade():
    for table in (ChatConversation.__table__, ChatTurn.__table__):
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    # Preserve private conversation history on application rollback.
    pass
