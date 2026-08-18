"""FORGE Backend — YouTube URL → Deployed Software pipeline."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field

from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.models import ForgeJob, JobStatus, StageName
from app.store import job_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm connections, ensure dirs
    job_store.init()
    yield
    # Shutdown
    job_store.close()


app = FastAPI(
    title="FORGE API",
    description="YouTube URL → Deployed Software",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,https://forge-n3oc73sh8-garv1.vercel.app").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    youtube_url: HttpUrl
    options: dict[str, Any] = Field(default_factory=dict)


class ProcessResponse(BaseModel):
    project_id: str
    status: JobStatus


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "forge-backend",
        "version": "0.1.0",
        "pipeline_ready": True,
    }


@app.post("/v1/forge/process", response_model=ProcessResponse)
async def process_youtube(req: ProcessRequest, bg: BackgroundTasks):
    """Start a full FORGE pipeline job."""
    job = job_store.create_job(str(req.youtube_url), req.options)
    orchestrator = PipelineOrchestrator(job.id)
    bg.add_task(orchestrator.run)
    return ProcessResponse(project_id=job.id, status=job.status)


@app.get("/v1/forge/{project_id}")
async def get_project(project_id: str):
    job = job_store.get_job(project_id)
    if not job:
        raise HTTPException(404, "Project not found")
    return job.model_dump()


@app.get("/v1/forge/{project_id}/stages")
async def get_stages(project_id: str):
    job = job_store.get_job(project_id)
    if not job:
        raise HTTPException(404, "Project not found")
    return {"stages": [s.model_dump() for s in job.stages]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
