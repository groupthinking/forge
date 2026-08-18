"""
FORGE Pipeline Orchestrator

Runs the 6-stage YouTube → Deployed Software pipeline asynchronously.
Each stage is a self-contained worker with progress reporting, artifact
handoff, and fail-closed error handling.

Stages (from forge-spec):
  1. Ingest
  2. Hybrid Transcribe
  3. Analyze + Extract
  4. Synthesize
  5. Validate + Test
  6. Build & Deploy
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any, Optional

from app.pipeline.models import (
    ForgeJob,
    JobStatus,
    Stage,
    StageName,
    StageStatus,
)
from app.pipeline.stages.ingest import IngestStage
from app.pipeline.stages.hybrid_transcribe import HybridTranscribeStage
from app.pipeline.stages.analyze_extract import AnalyzeExtractStage
from app.pipeline.stages.synthesize import SynthesizeStage
from app.pipeline.stages.validate_test import ValidateTestStage
from app.pipeline.stages.build_deploy import BuildDeployStage
from app.store import job_store

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Coordinates sequential execution of all FORGE stages for a job."""

    STAGE_ORDER = [
        StageName.ingest,
        StageName.hybrid_transcribe,
        StageName.analyze_extract,
        StageName.synthesize,
        StageName.validate_test,
        StageName.build_deploy,
    ]

    def __init__(self, job_id: str):
        self.job_id = job_id
        self._context: dict[str, Any] = {}  # shared artifacts between stages

    async def run(self) -> None:
        """Execute the full pipeline. Safe to run as a BackgroundTask."""
        job = job_store.get_job(self.job_id)
        if not job:
            logger.error("Job %s not found — aborting orchestrator", self.job_id)
            return

        job_store.set_status(self.job_id, JobStatus.running)
        logger.info("Pipeline started for job %s | url=%s", self.job_id, job.youtube_url)

        try:
            for stage_name in self.STAGE_ORDER:
                await self._run_stage(job, stage_name)
                # Refresh job after each stage
                job = job_store.get_job(self.job_id)
                if not job or job.status == JobStatus.failed:
                    return

            # Final success
            job = job_store.get_job(self.job_id)
            if job:
                job.status = JobStatus.complete
                job.updated_at = datetime.utcnow()
                # Pull live_url / github_repo from final context if present
                if "live_url" in self._context:
                    job.live_url = self._context["live_url"]
                if "github_repo" in self._context:
                    job.github_repo = self._context["github_repo"]
                job_store.update_job(job)
                logger.info(
                    "Pipeline COMPLETE job=%s live_url=%s",
                    self.job_id,
                    job.live_url,
                )

        except Exception as exc:
            logger.exception("Pipeline fatal error job=%s: %s", self.job_id, exc)
            job = job_store.get_job(self.job_id)
            if job:
                job.status = JobStatus.failed
                job.updated_at = datetime.utcnow()
                # Mark current running stage as failed
                for s in job.stages:
                    if s.status == StageStatus.running:
                        s.status = StageStatus.failed
                        s.error = str(exc)
                        s.finished_at = datetime.utcnow()
                job_store.update_job(job)

    async def _run_stage(self, job: ForgeJob, stage_name: StageName) -> None:
        stage = next((s for s in job.stages if s.name == stage_name), None)
        if not stage:
            raise RuntimeError(f"Stage {stage_name} missing from job model")

        stage.status = StageStatus.running
        stage.started_at = datetime.utcnow()
        stage.progress = 0
        stage.message = f"Starting {stage_name.value}..."
        job_store.update_job(job)

        worker = self._get_worker(stage_name)
        try:
            # Run worker; it mutates self._context and reports progress via callback
            await worker.execute(
                youtube_url=job.youtube_url,
                options=job.options,
                context=self._context,
                progress_cb=lambda p, msg: self._update_progress(stage_name, p, msg),
            )

            stage.status = StageStatus.complete
            stage.progress = 100
            stage.message = "complete"
            stage.finished_at = datetime.utcnow()
            stage.artifacts = {
                k: v
                for k, v in self._context.items()
                if k.startswith(stage_name.value) or k in ("transcript", "prd", "source_zip", "live_url", "github_repo")
            }
            job_store.update_job(job)
            logger.info("Stage %s complete for job %s", stage_name.value, self.job_id)

        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("Stage %s failed job=%s: %s\n%s", stage_name.value, self.job_id, exc, tb)
            stage.status = StageStatus.failed
            stage.error = str(exc)
            stage.message = f"failed: {exc}"
            stage.finished_at = datetime.utcnow()
            job.status = JobStatus.failed
            job_store.update_job(job)
            raise

    def _update_progress(self, stage_name: StageName, progress: int, message: str) -> None:
        job = job_store.get_job(self.job_id)
        if not job:
            return
        for s in job.stages:
            if s.name == stage_name:
                s.progress = min(100, max(0, progress))
                s.message = message
                break
        job_store.update_job(job)

    def _get_worker(self, stage_name: StageName):
        mapping = {
            StageName.ingest: IngestStage(),
            StageName.hybrid_transcribe: HybridTranscribeStage(),
            StageName.analyze_extract: AnalyzeExtractStage(),
            StageName.synthesize: SynthesizeStage(),
            StageName.validate_test: ValidateTestStage(),
            StageName.build_deploy: BuildDeployStage(),
        }
        return mapping[stage_name]
