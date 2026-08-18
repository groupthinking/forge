"""Simple in-memory job store. Replace with Redis + Postgres for production."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.pipeline.models import ForgeJob, JobStatus


class JobStore:
    def __init__(self):
        self._jobs: dict[str, ForgeJob] = {}

    def init(self):
        pass

    def close(self):
        pass

    def create_job(self, youtube_url: str, options: dict) -> ForgeJob:
        job = ForgeJob(youtube_url=youtube_url, options=options or {})
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Optional[ForgeJob]:
        return self._jobs.get(job_id)

    def update_job(self, job: ForgeJob) -> ForgeJob:
        job.updated_at = datetime.utcnow()
        self._jobs[job.id] = job
        return job

    def set_status(self, job_id: str, status: JobStatus):
        job = self._jobs.get(job_id)
        if job:
            job.status = status
            job.updated_at = datetime.utcnow()


job_store = JobStore()
