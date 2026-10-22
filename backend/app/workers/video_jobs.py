"""Durable single-concurrency video worker.

Run with: python -m app.workers.video_jobs
"""
import logging
import signal
import time

from app.core.config import settings
from app.database import SessionLocal
from app.models.video_job import VideoJobStatus, VideoProcessingJob
from app.services.video_processing import process_video_job
from app.services.video_storage import storage_node_id, storage_queue_stage, storage_root

logger = logging.getLogger(__name__)
stopping = False


def _stop(_signum, _frame):
    global stopping
    stopping = True


def recover_interrupted_jobs(db):
    jobs = db.query(VideoProcessingJob).filter(
        VideoProcessingJob.status == VideoJobStatus.PROCESSING).all()
    node_id = storage_node_id()
    jobs = [job for job in jobs if (job.summary or {}).get("_storage_node_id") == node_id]
    for job in jobs:
        job.status = VideoJobStatus.CANCELLED
        job.stage = storage_queue_stage()
    if jobs:
        db.commit()
        logger.warning("Requeued %s interrupted video job(s)", len(jobs))


def claim_next_job(db):
    job = (db.query(VideoProcessingJob)
           .filter(VideoProcessingJob.status == VideoJobStatus.CANCELLED,
                    VideoProcessingJob.stage == storage_queue_stage(),
                   VideoProcessingJob.cancel_requested.is_(False))
           .order_by(VideoProcessingJob.created_at)
           .with_for_update(skip_locked=True).first())
    if not job:
        return None
    job.status = VideoJobStatus.PROCESSING
    job.stage = "claimed"
    db.commit()
    return job.id


def main():
    logging.basicConfig(level=settings.LOG_LEVEL)
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    with SessionLocal() as db:
        recover_interrupted_jobs(db)
    logger.info(
        "Video worker started with single inference concurrency; media_root=%s",
        storage_root(),
    )
    while not stopping:
        with SessionLocal() as db:
            job_id = claim_next_job(db)
        if job_id:
            with SessionLocal() as db:
                process_video_job(db, job_id)
        else:
            time.sleep(settings.VIDEO_WORKER_POLL_SECONDS)
    logger.info("Video worker stopped")


if __name__ == "__main__":
    main()
