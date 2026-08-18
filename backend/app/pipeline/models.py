"""Pipeline domain models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


class StageName(str, Enum):
    ingest = "ingest"
    hybrid_transcribe = "hybrid_transcribe"
    analyze_extract = "analyze_extract"
    synthesize = "synthesize"
    validate_test = "validate_test"
    build_deploy = "build_deploy"


class StageStatus(str, Enum):
    idle = "idle"
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


class Stage(BaseModel):
    name: StageName
    status: StageStatus = StageStatus.idle
    progress: int = 0
    message: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    artifacts: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ForgeJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    youtube_url: str
    options: dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.queued
    stages: list[Stage] = Field(default_factory=list)
    live_url: Optional[str] = None
    github_repo: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def __init__(self, **data):
        super().__init__(**data)
        if not self.stages:
            self.stages = [
                Stage(name=StageName.ingest),
                Stage(name=StageName.hybrid_transcribe),
                Stage(name=StageName.analyze_extract),
                Stage(name=StageName.synthesize),
                Stage(name=StageName.validate_test),
                Stage(name=StageName.build_deploy),
            ]
