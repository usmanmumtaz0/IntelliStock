"""Persistent uploaded-video and bounded camera processing jobs."""
from alembic import op
import sqlalchemy as sa

revision = "0009_video_processing_jobs"
down_revision = "0008_rbac_requests_sessions"
branch_labels = None
depends_on = None

TABLES = ("video_processing_jobs", "video_frames", "video_detections")


def upgrade():
    bind = op.get_bind()
    from app.models.video_job import VideoDetection, VideoFrame, VideoProcessingJob

    VideoProcessingJob.__table__.create(bind, checkfirst=True)
    VideoFrame.__table__.create(bind, checkfirst=True)
    VideoDetection.__table__.create(bind, checkfirst=True)
    if bind.dialect.name == "postgresql":
        roles = [role for role in ("anon", "authenticated") if bind.execute(
            sa.text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}).scalar()]
        for table in TABLES:
            op.execute(sa.text(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY'))
            op.execute(sa.text(f'REVOKE ALL PRIVILEGES ON TABLE public."{table}" FROM PUBLIC'))
            for role in roles:
                op.execute(sa.text(
                    f'REVOKE ALL PRIVILEGES ON TABLE public."{table}" FROM "{role}"'))


def downgrade():
    # Processing evidence is intentionally preserved on code rollback.
    pass
