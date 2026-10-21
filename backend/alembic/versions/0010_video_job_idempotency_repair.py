"""Reconcile development databases that created the draft video table before 0009."""
from alembic import op
import sqlalchemy as sa

revision = "0010_video_job_idempotency"
down_revision = "0009_video_processing_jobs"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("video_processing_jobs")}
    if "idempotency_key" not in columns:
        op.add_column("video_processing_jobs", sa.Column("idempotency_key", sa.String(128), nullable=True))
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("video_processing_jobs")}
    if "uq_video_jobs_owner_idempotency" not in indexes:
        op.create_index("uq_video_jobs_owner_idempotency", "video_processing_jobs",
                        ["owner_user_id", "idempotency_key"], unique=True)


def downgrade():
    # Job identity and evidence are intentionally preserved on code rollback.
    pass
