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

logger = logging.getLogger(__name__)
stopping = False


def _stop(_signum, _frame):
    global stopping
    stopping = True


def recover_interrupted_jobs(db):
    jobs = db.query(VideoProcessingJob).filter(
        VideoProcessingJob.status == VideoJobStatus.PROCESSING).all()
    for job in jobs:
        job.status = VideoJobStatus.QUEUED
        job.stage = "recovered_after_worker_restart"
    if jobs:
        db.commit()
        logger.warning("Requeued %s interrupted video job(s)", len(jobs))


def claim_next_job(db):
    job = (db.query(VideoProcessingJob)
           .filter(VideoProcessingJob.status == VideoJobStatus.QUEUED,
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
    logger.info("Video worker started with single inference concurrency")
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
